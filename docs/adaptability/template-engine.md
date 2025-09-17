# LG V2 и новый движок шаблонизации

Анализируя требования по необходимости реализации новых блоков в шаблонах: условных и режимов, учитывая уже существующую логику прейсхолдеров с рекурсивными инклудами и предвосхищая новые потенциальные требования, связанные с системой шаблонов — я пришел к выводу о том, что нам необходимо разработать новый движок шаблонов и полностью переработать центральную часть пайплайна LG, которая будет использовать новую подсистему шаблонов. По сути это означает глобальный выпуск мажорной версии LG V2.

## Мы отказываемся от

1. Старый модуль `lg/context/`. Он не перспективен, основан на простой подстановке плейсхолдеров (`${section_name}`) и не поддерживает условные блоки или переопределение режимов. 

2. Центральная часть пайплайна в `lg/engine.py`.

```
resolve_context  → build_manifest → build_plan → process_groups → render_by_section → compose_context 
```

Основная проблема в том, что обработка шаблонов сейчас происходит в двух отдельных фазах:

- В `resolve_context` - собираются ссылки на секции из плейсхолдеров
- В `compose_context` - выполняется подстановка уже отрендеренных секций

А между этими фазами выполняется вся тяжелая работа по обработке файлов.

3. Старая система IR-классов в `lg/types.py`. Так как мы собираемся значительно переработать пайплайн, то от старой декларации IR-модели лучше тоже сразу отказаться и начать разработку более чистой подходящей версии.


## Что мы планируем на замену

### Новый единый движок шаблонизации

#### Общая структура движка шаблонизации

Мы создадим новый модуль `lg/template/` со следующими компонентами:

```
lg/template/
  ├─ lexer.py         # Лексический анализатор для шаблонов
  ├─ parser.py        # Построение AST из токенов
  ├─ evaluator.py     # Вычисление условий и режимов
  └─ process.py       # Однопроходный финальный резолвинг секций и рендеринг AST, внешнее API для `lg/engine_v2.py`
```

#### Новая структура AST для шаблонов

```python
@dataclass
class TemplateNode:
    """Базовый класс для всех узлов AST шаблона."""
    pass

@dataclass
class TextNode(TemplateNode):
    """Обычный текстовый контент."""
    text: str

@dataclass
class SectionNode(TemplateNode):
    """Плейсхолдер секции ${section}."""
    section_name: str
    # Метаданные для резолвинга
    resolved_ref: Optional[SectionRef] = None

@dataclass
class IncludeNode(TemplateNode):
    """Плейсхолдер для включения шаблона ${tpl:name} или ${ctx:name}."""
    kind: str  # "tpl" или "ctx"
    name: str
    origin: str  # "self" или путь
    # Для хранения вложенного AST после резолвинга
    children: List[TemplateNode] = field(default_factory=list)

@dataclass
class ConditionalBlockNode(TemplateNode):
    """Блок {% if condition %}...{% endif %}."""
    condition_text: str  # Исходный текст условия
    condition_ast: Optional[Condition] = None  # AST условия после парсинга
    body: List[TemplateNode] = field(default_factory=list)
    evaluated: Optional[bool] = None  # Результат после вычисления

@dataclass
class ModeBlockNode(TemplateNode):
    """Блок {% mode modeset:mode %}...{% endmode %}."""
    modeset: str
    mode: str
    body: List[TemplateNode] = field(default_factory=list)
    original_mode_options: Optional[ModeOptions] = None  # Сохраненный контекст перед блоком
    original_active_tags: Optional[Set[str]] = None  # Сохраненный контекст перед блоком
```

### Новая версия центрального пайплайна обработки LG V2

На замену старому `lg/engine.py` должен быть написан новый `lg/engine_v2.py`, который позволяет делать однопроходную работу с движком шаблонов.

По сути вместо того, чтобы 2 раза дергать систему шаблонизации (как в старой версии)? `lg/engine_v2.py` из `lg/template/process.py` вызывает один метод и ему передает один или несколько заранее сформированных хендлеров, которые инкапсулируют логику цепочки: build_manifest → build_plan → process_groups → render_by_section.

Таким образом, не умея самостоятельно производить фильтрацию файлов, работать с VCS, языковыми адаптерами и рендерить итоговые секции в fanced-блоки, шаблонизатор через хендлер (один или несколько) все равно получает возможность выполнить эти задачи. Это сокращает необходимость в объёмной промежуточной IR-модели.

<!-- TODO Тут необходимо нарисовать сиквенс диаграмму -->

#### Новый RunContext для отслеживания режимов и тегов

Скорее всего в новой версии LG V2 также необходимо будет скорректировать `RunContext`, так как сейчас в старом варианте это глобальный объект, который проходит через весь пайплайн как иммутабельный синглтон.

Когда в шаблоне встречается блок вида `{% mode modeset:mode %}...{% endmode %}`, нам нужно:
1. Временно изменить режимы и активные теги
2. Обработать содержимое блока с этими измененными настройками
3. Вернуть исходные режимы и теги после блока

Поэтому необходимо будет написать новую версию `RunContext` для шаблонизатора:

1. **Создать локальный контекст для шаблонизатора**:
   ```python
   @dataclass
   class TemplateRenderingContext:
       # Постоянные данные, как в старом RunContext
       …
       # Локальные переопределения
       current_mode_options: ModeOptions
       current_active_tags: Set[str]
       # Стек сохраненных состояний для вложенных блоков
       saved_states: List[Tuple[ModeOptions, Set[str]]] = field(default_factory=list)
   ```

2. **Реализовать методы для работы с режимами**:
   ```python
   def enter_mode_block(self, modeset: str, mode: str) -> None:
       # Сохраняем текущее состояние в стек
       self.saved_states.append((
           self.current_mode_options,
           self.current_active_tags
       ))
       
       # Применяем новый режим и обновляем теги
       new_options = self.run_ctx.adaptive_loader.get_mode_options(modeset, mode)
       new_tags = self.run_ctx.adaptive_loader.get_tags_for_mode(modeset, mode)
       
       # Создаем новые копии, чтобы избежать мутирования
       self.current_mode_options = ModeOptions.merge(self.current_mode_options, new_options)
       self.current_active_tags = self.current_active_tags.union(new_tags)
       
   def exit_mode_block(self) -> None:
       # Восстанавливаем предыдущее состояние из стека
       if self.saved_states:
           self.current_mode_options, self.current_active_tags = self.saved_states.pop()
   ```

3. **Использовать этот контекст при обработке AST шаблона**:
   ```python
   def evaluate_template(ast: List[TemplateNode], template_ctx: TemplateRenderingContext) -> str:
       result = []
       for node in ast:
           if isinstance(node, ModeBlockNode):
               template_ctx.enter_mode_block(node.modeset, node.mode)
               result.append(evaluate_template(node.body, template_ctx))
               template_ctx.exit_mode_block()
           # Обработка других типов узлов...
       return "".join(result)
   ```

## Что делаем сейчас

Давай осудим предложенный мною план переработки системы шаблонизации и центрального пайплайна. При анализе учитывай уже существующий код (чтобы не сломать старый функционал) ил новые поступившие требования.

Я предложил общее видение, но в предложенной мною архитектуре явно есть пробелы. Так что было бы полезно, если бы ты что-то детализировал и дорисовал необходимое диаграммы и схемы.

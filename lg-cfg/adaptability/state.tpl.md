## Текущий статус разработки функционального блока «Адаптивные возможности»

### Анализ существующего кода и точек интеграции

Текущая архитектура LG построена вокруг следующих основных компонентов:

1. **Конфигурация** (config) - загрузка и обработка YAML-конфигураций
2. **Контексты** (context) - шаблоны, контексты и плейсхолдеры
3. **Манифесты** (manifest) - построение файловых манифестов на основе фильтров
4. **Рендеринг** (render) - преобразование обработанных файлов в итоговый текст
5. **Адаптеры** (adapters) - обработка файлов разных форматов
6. **Статистика** (stats) - подсчет токенов и формирование отчетов
7. **CLI** (cli.py) - интерфейс командной строки

#### Точки расширения

Для внедрения адаптивных возможностей мы выделяем следующие ключевые точки расширения:

1. **Загрузка конфигурации режимов и тегов**
   - Новые файлы: `modes.yaml`, `tags.yaml`
   - Интеграция с существующей системой конфигурации

2. **Контекст выполнения**
   - Расширение `RunContext` для хранения активных режимов и тегов

3. **Обработка шаблонов**
   - Добавление поддержки условной логики (`{% if ... %}`)
   - Поддержка блоков режимов (`{% mode ... %}`)

4. **Фильтрация файлов**
   - Расширение модели фильтров для поддержки условной логики

5. **CLI**
   - Новые параметры для управления режимами и тегами
   - Новые команды для вывода информации о доступных режимах и тегах
   - Логика работы с `vcs.changed_files` теперь работает с опцией `vcs_mode` от активного режима, а не с аргументом `--mode` из CLI

### Новые модули и их назначение

#### 1. Система конфигурации режимов и тегов

```
lg/config/
  ├── modes.py      # Загрузка и обработка режимов
  ├── tags.py       # Загрузка и обработка тегов
  └── adaptive.py   # Общая логика адаптивной системы
```

##### Ключевые классы и функции:

```python
# modes.py
@dataclass
class Mode:
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModeSet:
    title: str
    modes: Dict[str, Mode] = field(default_factory=dict)

def load_modes(root: Path) -> Dict[str, ModeSet]:
    """Загрузка режимов с учетом иерархии скоупов"""
    ...

# tags.py
@dataclass
class Tag:
    title: str
    description: str = ""

@dataclass
class TagSet:
    title: str
    tags: Dict[str, Tag] = field(default_factory=dict)

def load_tags(root: Path) -> Tuple[Dict[str, TagSet], Dict[str, Tag]]:
    """Загрузка наборов тегов и глобальных тегов с учетом иерархии скоупов"""
    ...
```

#### 2. Система условий

```
lg/conditions/
  ├── __init__.py
  ├── parser.py     # Парсер условных выражений
  ├── evaluator.py  # Вычислитель условий
  └── model.py      # Модели условных выражений
```

##### Ключевые классы и функции:

```python
# model.py
@dataclass
class Condition:
    """Базовый класс для условий"""
    pass

@dataclass
class TagCondition(Condition):
    tag_name: str
    negated: bool = False

@dataclass
class TagSetCondition(Condition):
    set_name: str
    tag_name: str

@dataclass
class BinaryCondition(Condition):
    operator: str  # "AND" или "OR"
    left: Condition
    right: Condition

@dataclass
class ScopeCondition(Condition):
    scope_type: str  # "local" или "parent"

# parser.py
def parse_condition(condition_str: str) -> Condition:
    """Парсинг строки условия в объект Condition"""
    ...

# evaluator.py
def evaluate_condition(condition: Condition, context: ConditionContext) -> bool:
    """Вычисление условия на основе активных тегов и режимов"""
    ...

@dataclass
class ConditionContext:
    active_tags: Set[str]
    tagsets: Dict[str, Set[str]]
    current_scope: str = ""
    parent_scope: str = ""
```

#### 3. Расширения шаблонизатора

```
lg/templates/
  ├── __init__.py
  ├── conditional.py  # Обработка условных блоков
  └── mode_blocks.py  # Обработка блоков режимов
```

##### Ключевые классы и функции:

```python
# conditional.py
@dataclass
class ConditionalBlock:
    condition: Condition
    content: str
    else_content: Optional[str] = None

def parse_conditional_blocks(template_text: str) -> List[Union[str, ConditionalBlock]]:
    """Разбор шаблона на текст и условные блоки"""
    ...

def render_with_conditions(blocks: List[Union[str, ConditionalBlock]], context: ConditionContext) -> str:
    """Рендеринг шаблона с учетом условий"""
    ...

# mode_blocks.py
@dataclass
class ModeBlock:
    mode_set: str
    mode: str
    content: str

def parse_mode_blocks(template_text: str) -> List[Union[str, ModeBlock]]:
    """Разбор шаблона на текст и блоки режимов"""
    ...

def process_mode_blocks(blocks: List[Union[str, ModeBlock]], active_modes: Dict[str, str]) -> str:
    """Обработка блоков режимов"""
    ...
```

#### 4. Расширение контекста выполнения

```python
# run_context.py
@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    tokenizer: TokenService
    active_modes: Dict[str, str] = field(default_factory=dict)  # modeset_name -> mode_name
    active_tags: Set[str] = field(default_factory=set)  # все активные теги
    
    def get_condition_context(self) -> ConditionContext:
        """Создание контекста для вычисления условий"""
        ...
```

#### 5. Обновления в системе фильтрации

```python
# io/model.py
@dataclass
class ConditionalFilterRule:
    condition: Condition
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    
@dataclass
class FilterNode:
    mode: Mode
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    children: Dict[str, "FilterNode"] = field(default_factory=dict)
    when: List[ConditionalFilterRule] = field(default_factory=list)  # новое поле
```

#### 6. Обновления CLI

```python
# cli.py
def _build_parser() -> argparse.ArgumentParser:
    # ...существующий код...
    
    # Добавление новых параметров
    p.add_argument("--mode", action="append", help="активный режим в формате 'modeset:mode'")
    p.add_argument("--tags", help="дополнительные теги, разделенные запятыми")
    
    # Добавление новых команд
    sp_list.add_argument("what", choices=["contexts", "sections", "models", "mode-sets", "tag-sets"], 
                        help="что вывести")
    
    # ...существующий код...
```

### План внедрения

#### [] Итерация 1: Основы и конфигурация

1. **[] Реализация базовых моделей данных**
   - Создание классов `Mode`, `ModeSet`, `Tag`, `TagSet` 
   - Реализация сериализации/десериализации для YAML

2. **[] Загрузка конфигурации**
   - Разработка загрузчиков `modes.yaml` и `tags.yaml`
   - Поддержка директивы `include` для федеративной конфигурации
   - Механизм объединения родительских/дочерних конфигураций

3. **[] Расширение RunContext**
   - Добавление полей для активных режимов и тегов
   - Обработка CLI-параметров для режимов и тегов

#### [] Итерация 2: Система условий

1. **[] Парсер условий**
   - Реализация модели для представления условий
   - Парсер для выражений условий с поддержкой операторов `tag`, `TAGSET`, `AND`, `OR`, `NOT`

2. **[] Вычислитель условий**
   - Реализация вычислителя условных выражений
   - Контекстно-зависимая оценка (`scope:local`, `scope:parent`)

3. **[] Фреймворк тестирования**
   - Модульные тесты для парсера условий
   - Модульные тесты для вычислителя условий

#### [] Итерация 3: Условные блоки в шаблонах

1. **[] Базовые условные блоки**
   - Реализация синтаксиса `{% if условие %} ... {% endif %}`
   - Интеграция с системой рендеринга шаблонов

2. **[] Блоки режимов**
   - Реализация синтаксиса `{% mode modeset:mode %} ... {% endmode %}`
   - Поддержка переопределения режимов в шаблонах

3. **[] Тестирование**
   - Модульные тесты для условных блоков
   - Интеграционные тесты для обработки шаблонов

#### [] Итерация 4: Интеграция условной фильтрации

1. **[] Условные фильтры**
   - Расширение узлов фильтрации с условиями `when`
   - Интеграция вычисления условий с обработкой фильтров

2. **[] Расширения конфигурации секций**
   - Обновление `SectionCfg` для поддержки условных конфигураций
   - Применение условий к конфигурации адаптеров

#### [] Итерация 5: CLI и документация

1. **[] Команды CLI**
   - Реализация команды `lg list mode-sets`
   - Реализация команды `lg list tag-sets`
   - Полная интеграция параметров `--mode` и `--tags`

2. **[] Документация**
   - Пользовательская документация по режимам и тегам
   - Примеры условных шаблонов
   - Руководство по миграции от старого стиля к условным шаблонам

3. **[] Примеры и тесты**
   - Примеры конфигураций
   - Сквозные тесты


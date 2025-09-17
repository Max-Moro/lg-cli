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

4. Старая система статистики в `lg/stats/report.py`.

## Что мы планируем на замену

- **Новый единый движок шаблонизации**
- **Новая версия центрального пайплайна обработки LG V2**
- **Новая последовательность обработки секций**
- **Новая IR-модель**
- **Новая инкрементальная система статистики**

## Новый единый движок шаблонизации

### Общая структура движка шаблонизации

Мы создадим новый модуль `lg/template/` со следующими компонентами:

```
lg/template/
  ├─ nodes.py           # Определения AST-узлов шаблона
  ├─ lexer.py           # Лексический анализатор для шаблонов
  ├─ parser.py          # Построение AST из токенов
  ├─ evaluator.py       # Вычисление условий и режимов
  ├─ context.py         # Контекст рендеринга шаблона
  ├─ errors.py          # Классы ошибок и обработка исключений
  └─ processor.py       # API для движка шаблонизации
```

### Новая структура AST для шаблонов

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
class ElseNode(TemplateNode):
    """Обработка {% else %} внутри условных блоков."""
    body: List[TemplateNode] = field(default_factory=list)

@dataclass
class ModeBlockNode(TemplateNode):
    """Блок {% mode modeset:mode %}...{% endmode %}."""
    modeset: str
    mode: str
    body: List[TemplateNode] = field(default_factory=list)
    original_mode_options: Optional[ModeOptions] = None  # Сохраненный контекст перед блоком
    original_active_tags: Optional[Set[str]] = None  # Сохраненный контекст перед блоком

@dataclass
class CommentNode(TemplateNode):
    """Блок {# комментарий #}, который игнорируется при рендеринге."""
    text: str
```

Также нужно детализировать структуру лексера и парсера:

```python
# lg/template/lexer.py
class TokenType(enum.Enum):
    TEXT = "TEXT"
    PLACEHOLDER_START = "PLACEHOLDER_START"  # ${
    PLACEHOLDER_END = "PLACEHOLDER_END"      # }
    DIRECTIVE_START = "DIRECTIVE_START"      # {%
    DIRECTIVE_END = "DIRECTIVE_END"          # %}
    COMMENT_START = "COMMENT_START"          # {#
    COMMENT_END = "COMMENT_END"              # #}
    IDENTIFIER = "IDENTIFIER"
    COLON = "COLON"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    # ... другие токены

@dataclass
class Token:
    type: TokenType
    value: str
    position: int
    line: int
    column: int  # Для точной диагностики ошибок
```

### Диаграмма классов для нового движка шаблонизации

```mermaid
classDiagram
    TemplateNode <|-- TextNode
    TemplateNode <|-- SectionNode
    TemplateNode <|-- IncludeNode
    TemplateNode <|-- ConditionalBlockNode
    TemplateNode <|-- ModeBlockNode
    TemplateNode <|-- CommentNode
    TemplateNode <|-- ElseNode

    class TemplateNode {
        <<abstract>>
    }
    
    class TextNode {
        +String text
    }
    
    class SectionNode {
        +String section_name
        +SectionRef resolved_ref
    }
    
    class IncludeNode {
        +String kind
        +String name
        +String origin
        +List~TemplateNode~ children
    }
    
    class ConditionalBlockNode {
        +String condition_text
        +Condition condition_ast
        +List~TemplateNode~ body
        +Boolean evaluated
    }
    
    class ElseNode {
        +List~TemplateNode~ body
    }
    
    class ModeBlockNode {
        +String modeset
        +String mode
        +List~TemplateNode~ body
        +ModeOptions original_mode_options
        +Set~String~ original_active_tags
    }
    
    class CommentNode {
        +String text
    }
    
    TemplateProcessor --> TemplateParser
    TemplateParser --> TemplateLexer
    TemplateProcessor --> TemplateContext
    TemplateContext --> RunContext
    
    class TemplateProcessor {
        +process_template()
        +evaluate_template()
    }
    
    class TemplateParser {
        +parse()
        +parse_directive()
    }
    
    class TemplateLexer {
        +tokenize()
        +next_token()
    }
    
    class TemplateContext {
        +RunContext run_ctx
        +ModeOptions current_options
        +Set~String~ active_tags
        +Map active_modes
        +List saved_states
    }
    
    class RunContext {
        +RunOptions options
        +VcsProvider vcs
        +Cache cache
        +TokenService tokenizer
    }
```

## Новая версия центрального пайплайна обработки LG V2

На замену старому `lg/engine.py` должен быть написан новый `lg/engine_v2.py`, который позволяет делать однопроходную работу с движком шаблонов.

По сути вместо того, чтобы 2 раза дергать систему шаблонизации (как в старой версии)? `lg/engine_v2.py` из `lg/template/process.py` вызывает один метод и ему передает один или несколько заранее сформированных хендлеров, которые инкапсулируют логику цепочки: build_manifest → build_plan → process_groups → render_by_section.

Таким образом, не умея самостоятельно производить фильтрацию файлов, работать с VCS, языковыми адаптерами и рендерить итоговые секции в fanced-блоки, шаблонизатор через хендлер (один или несколько) все равно получает возможность выполнить эти задачи. Это сокращает необходимость в объёмной промежуточной IR-модели.

```mermaid
sequenceDiagram
    participant CLI
    participant engine_v2
    participant template.process
    participant section_processor
    
    CLI->>engine_v2: run_render_v2
    engine_v2->>engine_v2: _build_run_ctx
    engine_v2->>engine_v2: resolve_template
    engine_v2->>template.process: process_template
    
    template.process->>template.process: parse_template
    template.process->>template.process: evaluate_template
    
    Note over template.process, section_processor: ВСТРЕТИЛИ ${section}
    template.process->>section_processor: section placeholder found
    section_processor->>section_processor: build_manifest
    section_processor->>section_processor: build_plan
    section_processor->>section_processor: process_groups
    section_processor->>section_processor: render_section
    section_processor-->>template.process: section_rendered_text
    
    Note over template.process: ВСТРЕТИЛИ {% if ... %}
    template.process->>template.process: evaluate_condition
    
    Note over template.process: ВСТРЕТИЛИ {% mode ... %}
    template.process->>template.process: enter_mode_block
    Note over template.process: РЕКУРСИВНО ОБРАБАТЫВАЕМ ВЛОЖЕННЫЙ КОНТЕНТ
    template.process->>template.process: exit_mode_block
    
    template.process-->>engine_v2: rendered_result
    engine_v2-->>CLI: rendered_result
```

## Новая последовательность обработки секций

Переход к архитектуре, основанной на шаблонах, в LG V2 требует переосмысления обработки секций. Вместо пакетной обработки всех секций сразу нам нужен обработчик по запросу, который обрабатывает секции индивидуально по мере их встречи в шаблонах.

### Основной дизайн обработчика секций

Компонент обработчика секций будет выполнять полный цикл обработки одной секции по запросу от движка шаблонов:

```mermaid
flowchart LR
    TemplateEngine["Движок шаблонов"]
    SectionProcessor["Обработчик секций"]
    
    TemplateEngine -- "Встречает ${section}" --> SectionProcessor
    SectionProcessor -- "Отрендеренный текст" --> TemplateEngine
    
    subgraph SectionProcessor
        SR["Разрешение секции"] --> SM["Построение манифеста"]
        SM --> SP["Построение плана"]
        SP --> PF["Обработка файлов"]
        PF --> RS["Рендеринг секции"]
    end
```

### Новая IR модель для обработки секций

Вот предлагаемая IR модель для обработчика секций по запросу:

```python
# lg/types_v2.py

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Any

# Базовые типы
PathLabelMode = Literal["auto", "relative", "basename", "off"]
LangName = str  # "python", "markdown", "", и т.д.
LANG_NONE: LangName = ""

@dataclass(frozen=True)
class SectionRef:
    """Ссылка на секцию с информацией о разрешении."""
    name: str         # Имя секции, используемое в шаблоне
    scope_path: str   # Путь к директории области (относительно корня репозитория)
    cfg_path: Path    # Абсолютный путь к директории конфигурации
    
    def canon_key(self) -> str: # В однопроходной системе каноничный стабильный ключ уже не сильно нужен, но пусть на всякий случай будет
        """Возвращает канонический ключ для этой секции."""
        scope = self.scope_path or "."
        return f"{scope}::{self.name}"

@dataclass(frozen=True)
class FileEntry:
    """Представляет файл для включения в секцию."""
    abs_path: Path
    rel_path: str      # Относительно корня репозитория
    language_hint: LangName
    adapter_overrides: Dict[str, Dict] = field(default_factory=dict)

@dataclass
class SectionManifest:
    """Манифест одной секции со всеми её файлами."""
    ref: SectionRef
    files: List[FileEntry]
    # code_fence: bool — этого поля теперь нет, достается из TemplateContext.current_mode_options
    path_labels: PathLabelMode
    adapters_cfg: Dict[str, Dict] = field(default_factory=dict)

@dataclass
class FileGroup:
    """Группа файлов с одинаковым языком."""
    lang: LangName
    entries: List[FileEntry]
    mixed: bool = False

@dataclass
class SectionPlan:
    """План для рендеринга одной секции."""
    manifest: SectionManifest
    groups: List[FileGroup]
    md_only: bool
    labels: Dict[str, str] = field(default_factory=dict)  # rel_path -> отображаемая метка

@dataclass(frozen=True)
class ProcessedFile:
    """Обработанный файл, готовый для рендеринга."""
    abs_path: Path
    rel_path: str
    processed_text: str
    raw_text: str
    cache_key: str
    stats: FileStats

@dataclass
class RenderedSection:
    """Финальная отрендеренная секция."""
    ref: SectionRef
    text: str
    files: List[ProcessedFile]
    stats: SectionStats


# ----- Дополнительная IR-модель для новой подиммтемы статистики ----
# Пока что это концепт на стадии проработки
@dataclass
class FileStats:
    """Статистика по файлу."""
    size_bytes: int
    tokens_raw: int
    tokens_processed: int
    saved_tokens: int
    saved_pct: float
    meta: Dict[str, Any]

@dataclass
class SectionStats:
    """Статистика по отрендеренной секции."""
    tokens_processed: int
    tokens_raw: int
    total_size_bytes: int
    meta_summary: Dict[str, int] = field(default_factory=dict)

@dataclass
class TemplateStats:
    """Статистика по шаблону."""
    key: str
    tokens: int
    text_size: int
```

### Реализация обработчика секций

```python
# lg/section_processor.py

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

from .types_v2 import SectionRef, SectionManifest, SectionPlan, ProcessedFile, RenderedSection
from .run_context import RunContext
from .template.context import TemplateContext
from .cache.fs_cache import Cache

class SectionProcessor:
    """
    Обрабатывает одну секцию по запросу.
    Это заменяет части старой цепочки build_manifest -> build_plan -> process_groups -> render_by_section,
    но для одной секции за раз.
    """
    
    def __init__(self, run_ctx: RunContext):
        self.run_ctx = run_ctx
        self.cache = run_ctx.cache
        self.vcs = run_ctx.vcs
        self.section_cache: Dict[str, RenderedSection] = {}
    
    def process_section(self, section_name: str, template_ctx: TemplateContext) -> RenderedSection:
        """
        Обрабатывает одну секцию и возвращает её отрендеренное содержимое.
        
        Args:
            section_name: Имя секции для обработки
            template_ctx: Текущий контекст шаблона (содержит активные режимы, теги)
            
        Returns:
            Отрендеренная секция
        """
        # Сначала проверяем кэш
        cache_key = self._compute_cache_key(section_name, template_ctx)
        if cache_key in self.section_cache:
            return self.section_cache[cache_key]
        
        # Обрабатываем секцию через конвейер
        section_ref = self._resolve_section_ref(section_name, template_ctx)
        manifest = self._build_section_manifest(section_ref, template_ctx)
        plan = self._build_section_plan(manifest, template_ctx)
        processed_files = self._process_files(plan, template_ctx)
        rendered = self._render_section(plan, processed_files, template_ctx)
        
        # Кэшируем результат
        self.section_cache[cache_key] = rendered
        
        return rendered
    
    def _compute_cache_key(self, section_name: str, template_ctx: TemplateContext) -> str:
        """
        Вычисляет ключ кэша для секции на основе:
        - Имени секции
        - Активных режимов
        - Активных тегов
        - Режима VCS (all vs changes)
        """
        # Детали реализации
        pass
    
    # Другие методы реализации
    # ...
```

### Ключевые отличия от старого конвейера

1. **Обработка по запросу**: Секции обрабатываются индивидуально при встрече в шаблонах

2. **Контекстно-зависимая обработка**: Включаемые файлы зависят от активных режимов и тегов

3. **Динамическое кэширование**: Ключи кэша включают активные режимы/теги для корректного повторного использования

4. **Детальная фильтрация файлов**: Фильтрация файлов на основе активных условий

### Интеграция с движком шаблонов

Обработчик секций интегрируется с движком шаблонов следующим образом:

```python
class TemplateProcessor:
    def __init__(self, run_ctx: RunContext):
        self.run_ctx = run_ctx
        self.section_processor = SectionProcessor(run_ctx)
        self.template_ctx = TemplateContext(run_ctx)
        
    def process_template(self, template_text: str) -> str:
        """Обрабатывает шаблон и возвращает отрендеренный результат."""
        ast = self.parse_template(template_text)
        return self.evaluate_template(ast)
        
    def evaluate_template(self, ast: List[TemplateNode]) -> str:
        result = []
        for node in ast:
            if isinstance(node, SectionNode):
                # Здесь вызывается обработчик секций
                section = self.section_processor.process_section(
                    node.section_name, 
                    self.template_ctx
                )
                result.append(section.text)
            elif isinstance(node, ConditionalBlockNode):
                if self.evaluate_condition(node.condition_ast):
                    result.append(self.evaluate_template(node.body))
                elif node.else_block:
                    result.append(self.evaluate_template(node.else_block.body))
            elif isinstance(node, ModeBlockNode):
                self.template_ctx.enter_mode_block(node.modeset, node.mode)
                result.append(self.evaluate_template(node.body))
                self.template_ctx.exit_mode_block()
            # Обработка других типов узлов...
        return "".join(result)
```

### Контекст шаблона для управления состоянием

Контекст шаблона поддерживает состояние, необходимое во время обработки шаблона:

```python
@dataclass
class TemplateContext:
    """Контекст для рендеринга шаблона с управлением состоянием."""
    run_ctx: RunContext
    # Локальные переопределения
    current_mode_options: ModeOptions
    active_tags: Set[str]
    active_modes: Dict[str, str]  # modeset -> mode
    # Стек для вложенных блоков режимов
    saved_states: List[Tuple[ModeOptions, Set[str], Dict[str, str]]] = field(default_factory=list)
    
    def enter_mode_block(self, modeset: str, mode: str) -> None:
        """Сохраняет текущее состояние и применяет новый режим."""
        # Сохраняем текущее состояние
        self.saved_states.append((
            self.current_mode_options,
            set(self.active_tags),
            dict(self.active_modes)
        ))
        
        # Применяем новый режим
        self.active_modes[modeset] = mode
        mode_info = self.run_ctx.adaptive_loader.get_mode_info(modeset, mode)
        if mode_info:
            # Обновляем теги
            self.active_tags.update(mode_info.tags)
            # Обновляем опции режима
            self.current_mode_options = ModeOptions.merge(
                self.current_mode_options, 
                mode_info.options
            )
    
    def exit_mode_block(self) -> None:
        """Восстанавливает предыдущее состояние."""
        if self.saved_states:
            self.current_mode_options, self.active_tags, self.active_modes = self.saved_states.pop()
```

### Условная фильтрация файлов

Ключевое нововведение в этом дизайне — условная фильтрация файлов на основе активного контекста:

```python
def _filter_files_by_conditions(
    self, 
    files: List[FileEntry], 
    filters: Dict[str, Any], 
    template_ctx: TemplateContext
) -> List[FileEntry]:
    """Фильтрует файлы на основе условных правил из конфигурации."""
    result = list(files)  # Начинаем со всех файлов
    
    # Применяем условные фильтры
    if "when" in filters:
        for condition_rule in filters["when"]:
            condition = condition_rule.get("condition")
            if not condition:
                continue
                
            # Оцениваем условие с текущим контекстом
            is_match = self._evaluate_condition(condition, template_ctx)
            if is_match:
                # Применяем правила allow/block из этого условия
                if "allow" in condition_rule:
                    # Добавляем файлы, соответствующие шаблонам allow
                    pass
                if "block" in condition_rule:
                    # Удаляем файлы, соответствующие шаблонам block
                    pass
    
    return result
```

### Управление кэшем

Система кэширования должна быть обновлена для учета активного контекста шаблона:

```python
def _compute_section_cache_key(self, section_ref: SectionRef, template_ctx: TemplateContext) -> str:
    """Вычисляет ключ кэша, включая активные режимы и теги."""
    key_parts = [
        section_ref.canon_key(),
        template_ctx.current_mode_options.vcs_mode,
    ]
    
    # Добавляем активные режимы
    for modeset, mode in sorted(template_ctx.active_modes.items()):
        key_parts.append(f"mode:{modeset}:{mode}")
    
    # Добавляем активные теги
    for tag in sorted(template_ctx.active_tags):
        key_parts.append(f"tag:{tag}")
        
    return hashlib.sha256(":".join(key_parts).encode()).hexdigest()
```

## Что делаем сейчас

Ничего пока делать не нужно. Просто подтверди, что ты дочитал досюда.
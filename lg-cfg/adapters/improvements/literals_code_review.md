# Code Review: Literals Optimization Subsystem

**Дата**: 2025-12-13
**Scope**: `lg/adapters/optimizations/literals/*`
**Охват языков**: Python, TypeScript, Kotlin, C++, C, Java, JavaScript, Scala, Go, Rust

---

## Executive Summary

Подсистема оптимизации литералов успешно реализована для 10 языков и демонстрирует хорошую архитектурную основу. Однако расширение на новые языки выявило несколько проблемных зон:

**Критические проблемы**: 0
**Высокий приоритет**: 3
**Средний приоритет**: 5
**Низкий приоритет**: 4

**Общая оценка архитектуры**: ⭐⭐⭐⭐☆ (4/5)

---

## 1. Архитектурные проблемы

### 1.1 Дублирование логики детекции делимитеров (Высокий приоритет)

**Проблема**: Каждый языковой дескриптор дублирует схожую логику для `_detect_string_opening()` и `_detect_string_closing()`.

**Примеры дублирования**:

```python
# python/literals.py
def _detect_string_opening(text: str) -> str:
    stripped = text.strip()
    prefix_match = re.match(r'^([fFrRbBuU]{0,2})', stripped)
    prefix = prefix_match.group(1) if prefix_match else ""
    rest = stripped[len(prefix):]
    if rest.startswith('"""'):
        return f'{prefix}"""'
    if rest.startswith("'''"):
        return f"{prefix}'''"
    # ...

# kotlin/literals.py
def _detect_string_opening(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('"""'):
        return '"""'
    if stripped.startswith('"'):
        return '"'
    if stripped.startswith("'"):
        return "'"
    return '"'

# scala/literals.py
def _detect_string_opening(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('s"""') or stripped.startswith('f"""') or stripped.startswith('raw"""'):
        return stripped[:4]
    if stripped.startswith('"""'):
        return '"""'
    # ...
```

**Анализ**:
- Паттерн одинаковый: strip → check prefixes → check triple quotes → check single quotes
- Различия только в конкретных префиксах и порядке проверок
- 10 языков × 2 функции = 20 дублированных реализаций

**Рекомендация**: Создать базовый класс `DelimiterDetector` с параметризуемой конфигурацией:

```python
# utils/delimiter_detection.py
@dataclass
class DelimiterConfig:
    """Configuration for delimiter detection."""
    string_prefixes: List[str] = field(default_factory=list)  # e.g., ["f", "r", "b"]
    triple_quote_styles: List[str] = field(default_factory=lambda: ['"""', "'''"])
    single_quote_styles: List[str] = field(default_factory=lambda: ['"', "'"])
    raw_string_patterns: List[tuple] = field(default_factory=list)  # [(regex, template)]

class DelimiterDetector:
    def __init__(self, config: DelimiterConfig):
        self.config = config

    def detect_opening(self, text: str) -> str:
        """Universal opening delimiter detection."""
        stripped = text.strip()

        # Check for raw strings (Rust r#", C++ R"(...)")
        for pattern, template in self.config.raw_string_patterns:
            match = re.match(pattern, stripped)
            if match:
                return match.group(0)

        # Extract prefix if present
        prefix = ""
        if self.config.string_prefixes:
            prefix_pattern = f"^([{''.join(self.config.string_prefixes)}]{{0,2}})"
            match = re.match(prefix_pattern, stripped, re.IGNORECASE)
            if match:
                prefix = match.group(1)

        rest = stripped[len(prefix):]

        # Check triple quotes first
        for triple in self.config.triple_quote_styles:
            if rest.startswith(triple):
                return f"{prefix}{triple}"

        # Check single quotes
        for single in self.config.single_quote_styles:
            if rest.startswith(single):
                return f"{prefix}{single}"

        # Fallback
        return self.config.single_quote_styles[0] if self.config.single_quote_styles else '"'

    def detect_closing(self, text: str) -> str:
        """Universal closing delimiter detection."""
        stripped = text.strip()

        # Check for raw strings
        for pattern, template in self.config.raw_string_patterns:
            # Need closing pattern extraction logic
            pass

        # Check triple quotes
        for triple in self.config.triple_quote_styles:
            if stripped.endswith(triple):
                return triple

        # Check single quotes
        for single in self.config.single_quote_styles:
            if stripped.endswith(single):
                return single

        # Fallback
        return self.config.single_quote_styles[0] if self.config.single_quote_styles else '"'
```

**Использование**:
```python
# python/literals.py
PYTHON_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=["f", "F", "r", "R", "b", "B", "u", "U"],
    triple_quote_styles=['"""', "'''"],
    single_quote_styles=['"', "'"],
)
detector = DelimiterDetector(PYTHON_DELIMITER_CONFIG)

PYTHON_STRING_PROFILE = StringProfile(
    query="(string) @lit",
    opening=detector.detect_opening,
    closing=detector.detect_closing,
    # ...
)
```

**Выгоды**:
- Устранение 20 дублированных функций
- Единое место для багфиксов
- Упрощение добавления новых языков
- Явная документация паттернов через конфигурацию

---

### 1.2 Отсутствие валидации профилей (Средний приоритет)

**Проблема**: Профили создаются декларативно, но нет валидации их корректности на этапе создания дескриптора.

**Потенциальные баги**:
```python
# Забыли указать wrapper_match для FactoryProfile
BROKEN_FACTORY = FactoryProfile(
    query="...",
    opening="(",
    closing=")",
    separator=",",
    # wrapper_match="" — пустая строка, будет падать в runtime!
)

# Несовместимые placeholder_position и profile type
BROKEN_SEQUENCE = SequenceProfile(
    query="...",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.INLINE,  # INLINE только для StringProfile!
)
```

**Рекомендация**: Добавить `__post_init__` валидацию в профили:

```python
# patterns.py
@dataclass
class FactoryProfile(CollectionProfile):
    wrapper_match: str = ""

    def __post_init__(self):
        # Валидация wrapper_match
        if not self.wrapper_match or self.wrapper_match.strip() == "":
            raise ValueError(
                f"{self.__class__.__name__}: wrapper_match must be non-empty. "
                f"Got: {self.wrapper_match!r}"
            )

        # Валидация placeholder_position
        if self.placeholder_position == PlaceholderPosition.INLINE:
            raise ValueError(
                f"{self.__class__.__name__}: INLINE placeholder not supported. "
                f"Use END or MIDDLE_COMMENT."
            )

        super().__post_init__() if hasattr(super(), '__post_init__') else None

@dataclass
class StringProfile(LiteralProfile):
    def __post_init__(self):
        # Валидация interpolation
        if self.interpolation_markers:
            for marker in self.interpolation_markers:
                if not isinstance(marker, tuple) or len(marker) != 3:
                    raise ValueError(
                        f"Invalid interpolation marker: {marker}. "
                        f"Expected tuple of (prefix, opening, closing)."
                    )

        # Валидация placeholder_position
        if self.placeholder_position not in (PlaceholderPosition.INLINE, PlaceholderPosition.NONE):
            raise ValueError(
                f"{self.__class__.__name__}: only INLINE or NONE placeholder supported. "
                f"Got: {self.placeholder_position}"
            )
```

**Выгоды**:
- Раннее обнаружение ошибок конфигурации
- Fail-fast на этапе создания адаптера
- Явная документация ограничений

---

### 1.3 Неявная зависимость от порядка профилей (Средний приоритет)

**Проблема**: Порядок профилей в дескрипторе критичен, но это неявно и не документировано.

**Пример**:
```python
# javascript/literals.py
def create_javascript_descriptor() -> LanguageLiteralDescriptor:
    return LanguageLiteralDescriptor(
        profiles=[
            JS_TEMPLATE_STRING_PROFILE,  # ДОЛЖЕН быть ПЕРВЫМ!
            JS_STRING_PROFILE,            # Иначе `` будут матчиться как обычные строки
            JS_REGEX_PROFILE,
            JS_ARRAY_PROFILE,
            JS_OBJECT_PROFILE,
        ],
    )
```

**Риски**:
- При рефакторинге легко сломать порядок
- Неочевидно для новых разработчиков
- Нет проверки на конфликтующие query

**Рекомендация**: Добавить явную приоритезацию и валидацию:

```python
# patterns.py
@dataclass
class LiteralProfile:
    query: str
    priority: int = 100  # Меньше = выше приоритет

    # ...

# descriptor.py
@dataclass
class LanguageLiteralDescriptor:
    profiles: List[LiteralProfile] = field(default_factory=list)

    def __post_init__(self):
        # Автосортировка по приоритету
        self.profiles = sorted(self.profiles, key=lambda p: p.priority)

        # Проверка на конфликтующие query для одного типа
        from collections import defaultdict
        by_type = defaultdict(list)
        for p in self.profiles:
            by_type[type(p).__name__].append(p)

        # Проверка перекрывающихся query в пределах одного типа
        for profile_type, profiles in by_type.items():
            if len(profiles) > 1:
                # Можно добавить более сложную проверку через tree-sitter
                pass

# javascript/literals.py
JS_TEMPLATE_STRING_PROFILE = StringProfile(
    query="(template_string) @lit",
    priority=10,  # Высокий приоритет
    # ...
)

JS_STRING_PROFILE = StringProfile(
    query="(string) @lit",
    priority=20,  # Ниже priority
    # ...
)
```

**Выгоды**:
- Явная документация важности порядка
- Автоматическая сортировка
- Защита от ошибок при рефакторинге

---

## 2. Проблемы производительности

### 2.1 Избыточное создание ElementParser (Высокий приоритет)

**Проблема**: В `StandardCollectionsProcessor` кэш парсеров работает локально на инстанс компонента, но компонент создается для каждого файла в `LiteralPipeline.__init__`.

**Анализ**:
```python
# processing/pipeline.py
class LiteralPipeline:
    def __init__(self, cfg: LiteralConfig, adapter):
        # ...
        self.special_components: List[LiteralProcessor] = [
            # Создается КАЖДЫЙ РАЗ для каждого файла!
            StandardCollectionsProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
                self.selector,
                self.comment_formatter,
                self.descriptor
            ),
            # ...
        ]

# components/standard_collections.py
class StandardCollectionsProcessor(LiteralProcessor):
    def __init__(self, ...):
        # ...
        self._parsers: dict[str, ElementParser] = {}  # Кэш теряется при пересоздании!
```

**Проблема**: При обработке 100 файлов создается 100 кэшей `_parsers`, каждый заполняется заново.

**Рекомендация**: Вынести кэш парсеров на уровень shared сервисов:

```python
# utils/element_parser.py
class ElementParserFactory:
    """Singleton factory for ElementParser instances."""

    def __init__(self):
        self._cache: dict[str, ElementParser] = {}

    def get_parser(
        self,
        separator: str,
        kv_separator: Optional[str],
        tuple_size: int,
        factory_wrappers: List[str],
    ) -> ElementParser:
        """Get or create parser with caching."""
        key = f"{separator}:{kv_separator}:{tuple_size}:{hash(tuple(factory_wrappers))}"

        if key not in self._cache:
            config = ParseConfig(
                separator=separator,
                kv_separator=kv_separator,
                factory_wrappers=factory_wrappers,
            )
            self._cache[key] = ElementParser(config)

        return self._cache[key]

# processing/pipeline.py
class LiteralPipeline:
    def __init__(self, cfg: LiteralConfig, adapter):
        # ...
        self.parser_factory = ElementParserFactory()  # Shared factory

        self.special_components: List[LiteralProcessor] = [
            StandardCollectionsProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
                self.selector,
                self.comment_formatter,
                self.descriptor,
                self.parser_factory,  # Передаем фабрику
            ),
            # ...
        ]

# components/standard_collections.py
class StandardCollectionsProcessor(LiteralProcessor):
    def __init__(
        self,
        tokenizer: TokenService,
        literal_parser: LiteralParser,
        selector: BudgetSelector,
        comment_formatter: CommentFormatter,
        descriptor: LanguageLiteralDescriptor,
        parser_factory: ElementParserFactory,  # Новый параметр
    ):
        self.tokenizer = tokenizer
        self.parser = literal_parser
        self.selector = selector
        self.collection_formatter = CollectionFormatter(tokenizer, comment_formatter)
        self.descriptor = descriptor
        self.parser_factory = parser_factory  # Сохраняем фабрику

    def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
        """Get parser via factory (shared cache)."""
        separator = profile.separator
        kv_separator = profile.kv_separator if isinstance(profile, (MappingProfile, FactoryProfile)) else None
        tuple_size = profile.tuple_size if isinstance(profile, FactoryProfile) else 1
        factory_wrappers = ElementParser.collect_factory_wrappers_from_descriptor(self.descriptor)

        return self.parser_factory.get_parser(
            separator=separator,
            kv_separator=kv_separator,
            tuple_size=tuple_size,
            factory_wrappers=factory_wrappers,
        )
```

**Выгоды**:
- Кэш парсеров переиспользуется между файлами
- Снижение накладных расходов на создание ElementParser
- Более явная архитектура shared сервисов

---

### 2.2 Повторное вычисление factory_wrappers (Средний приоритет)

**Проблема**: `ElementParser.collect_factory_wrappers_from_descriptor()` вызывается в `_get_parser_for_profile()`, что происходит для каждого профиля при каждом литерале.

**Анализ**:
```python
# components/standard_collections.py
def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
    # ...
    factory_wrappers = ElementParser.collect_factory_wrappers_from_descriptor(self.descriptor)
    # Проходит по всем профилям дескриптора КАЖДЫЙ РАЗ!
```

**Рекомендация**: Предвычислить при создании компонента:

```python
class StandardCollectionsProcessor(LiteralProcessor):
    def __init__(self, ...):
        # ...
        # Вычислить один раз при инициализации
        self.factory_wrappers = ElementParser.collect_factory_wrappers_from_descriptor(
            self.descriptor
        )

    def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
        # Использовать предвычисленное значение
        return self.parser_factory.get_parser(
            separator=separator,
            kv_separator=kv_separator,
            tuple_size=tuple_size,
            factory_wrappers=self.factory_wrappers,  # Переиспользуем
        )
```

**Выгоды**:
- Снижение вычислительных затрат
- O(1) вместо O(n_profiles) на каждый литерал

---

### 2.3 Неэффективный поиск nested literals в BlockInit (Низкий приоритет)

**Проблема**: В `BlockInitProcessorBase._optimize_statement_recursive()` для каждого statement выполняется полный проход по всем профилям с tree-sitter query.

**Анализ**:
```python
# components/block_init.py
def _optimize_statement_recursive(self, stmt_node: Node, doc: TreeSitterDocument, token_budget: int) -> str:
    # ...
    def find_literals(node: Node, is_direct_child: bool = False):
        found_literal = False
        for profile in self.all_profiles:  # Перебор ВСЕХ профилей
            try:
                nodes = doc.query_nodes(profile.query, "lit")  # Tree-sitter query
                if node in nodes:
                    # ...
```

**Проблема**:
- Для statement с 5 дочерними узлами × 15 профилей = 75 tree-sitter запросов
- Большинство запросов возвращают пустой результат

**Рекомендация**: Предвычислить все литералы в документе один раз:

```python
class BlockInitProcessorBase(LiteralProcessor):
    def __init__(self, ...):
        # ...
        self._literal_nodes_cache: Optional[set] = None

    def _get_all_literal_nodes(self, doc: TreeSitterDocument) -> set:
        """Cache all literal nodes in document."""
        if self._literal_nodes_cache is None:
            self._literal_nodes_cache = set()
            for profile in self.all_profiles:
                try:
                    nodes = doc.query_nodes(profile.query, "lit")
                    self._literal_nodes_cache.update(
                        (n.start_byte, n.end_byte) for n in nodes
                    )
                except:
                    continue
        return self._literal_nodes_cache

    def _optimize_statement_recursive(self, stmt_node: Node, doc: TreeSitterDocument, token_budget: int) -> str:
        literal_coords = self._get_all_literal_nodes(doc)

        def find_literals(node: Node, is_direct_child: bool = False):
            coords = (node.start_byte, node.end_byte)
            if coords in literal_coords:
                # Найден literal node, обработать
                # ...
```

**Выгоды**:
- O(1) lookup вместо O(n_profiles × n_nodes) tree-sitter запросов
- Существенное ускорение на больших statement blocks

---

## 3. Проблемы поддерживаемости

### 3.1 Отсутствие документации для BlockInitProfile (Средний приоритет)

**Проблема**: `BlockInitProfile` — самый сложный паттерн, но его параметры (`block_selector`, `statement_pattern`) не документированы.

**Пример**:
```python
# java/literals.py
JAVA_DOUBLE_BRACE_PROFILE = BlockInitProfile(
    query="""
    (object_creation_expression
      (class_body
        (block))) @lit
    """,
    block_selector="class_body/block",  # ??? Что это значит?
    statement_pattern="*/method_invocation",  # ??? Синтаксис?
    # ...
)
```

**Рекомендация**: Добавить docstring в `BlockInitProfile`:

```python
@dataclass
class BlockInitProfile(LiteralProfile):
    """
    Profile for imperative block initialization patterns.

    Describes imperative initialization blocks like Java double-brace
    initialization and Rust HashMap initialization chains.

    Args:
        block_selector: Path to statements block within matched node.
            Format: "parent_type/child_type/..." (slash-separated path).
            Example: "class_body/block" navigates from object_creation_expression
            to class_body child, then to its block child.
            None means the matched node itself is the block.

        statement_pattern: Pattern to match repetitive statements.
            Format: [*/]node_type[field_name=value]
            - "*/method_invocation": Matches method_invocation anywhere in subtree
            - "method_invocation": Matches direct children only
            - "identifier[name=insert]": Matches identifier with specific field value
            Example: "*/method_invocation" matches all put() calls in Java double-brace.

        placeholder_position: Where to place trimming placeholder.
            Typically MIDDLE_COMMENT for statement blocks.

        min_elements: Minimum statements to keep, even if over budget.

    Examples:
        Java double-brace initialization:
        >>> profile = BlockInitProfile(
        ...     query='(object_creation_expression (class_body (block))) @lit',
        ...     block_selector="class_body/block",
        ...     statement_pattern="*/method_invocation",
        ...     placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
        ...     min_elements=1,
        ... )

        Rust HashMap let-group:
        >>> profile = BlockInitProfile(
        ...     query='(let_declaration ...) @lit',
        ...     block_selector=None,  # let_declaration itself contains the init
        ...     statement_pattern="*/call_expression",
        ...     placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
        ...     min_elements=1,
        ... )
    """

    block_selector: Optional[str] = None
    statement_pattern: Optional[str] = None
    # ...
```

**Выгоды**:
- Явная документация сложных параметров
- Примеры использования
- Упрощение добавления новых языков

---

### 3.2 Неявное поведение preserve_all_keys (Средний приоритет)

**Проблема**: Параметр `preserve_all_keys` в `MappingProfile` влияет только на top-level ключи, но это не документировано.

**Пример**:
```python
# go/literals.py
GO_STRUCT_PROFILE = MappingProfile(
    # ...
    preserve_all_keys=True,  # Что именно сохраняется?
)
```

**Рекомендация**: Улучшить документацию и переименовать:

```python
@dataclass
class MappingProfile(CollectionProfile):
    """
    Profile for mapping literal patterns.

    Args:
        preserve_all_keys: Preserve all keys/fields at TOP LEVEL ONLY.
            When True: all top-level keys are kept, optimization applied to nested values.
            Nested mappings are still subject to normal optimization.

            Use case: Typed struct literals where field names must be preserved.

            Example (Go struct):
                Original:
                    Config{
                        Host: "localhost",
                        Port: 8080,
                        Settings: map[string]string{
                            "key1": "value1",
                            "key2": "value2",
                            "key3": "value3",  // Many more...
                        }
                    }

                With preserve_all_keys=True:
                    Config{
                        Host: "localhost",  // Kept (top-level field)
                        Port: 8080,         // Kept (top-level field)
                        Settings: map[string]string{
                            "key1": "value1",
                            // ... (2 more, −50 tokens)  // Nested map optimized!
                        }
                    }
    """
    preserve_all_keys: bool = False
```

**Или переименовать**:
```python
preserve_top_level_keys: bool = False  # Более явное имя
```

**Выгоды**:
- Явное понимание scope параметра
- Предотвращение неправильных ожиданий

---

### 3.3 Дублирование comment style в компонентах (Низкий приоритет)

**Проблема**: `BlockInitProcessorBase` хранит `single_comment` и `block_comment`, хотя эта информация уже есть в `CommentFormatter`.

**Анализ**:
```python
# components/block_init.py
class BlockInitProcessorBase(LiteralProcessor):
    def __init__(self, ..., comment_style: tuple[str, tuple[str, str]]):
        # ...
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]
        # Дублирование! CommentFormatter уже знает comment_style
```

**Рекомендация**: Использовать `CommentFormatter` напрямую:

```python
class BlockInitProcessorBase(LiteralProcessor):
    def __init__(
        self,
        tokenizer,
        all_profiles: List[LiteralProfile],
        process_literal_callback: ProcessLiteralCallback,
        comment_formatter: CommentFormatter,  # Вместо comment_style
    ):
        self.tokenizer = tokenizer
        self.all_profiles = all_profiles
        self.process_literal_callback = process_literal_callback
        self.comment_formatter = comment_formatter  # Переиспользуем форматтер

    def _reconstruct_block(self, ...):
        # Использовать comment_formatter.single_comment вместо self.single_comment
        placeholder_comment = f"{self.comment_formatter.single_comment} … ({removed_count} more, −{tokens_saved} tokens)"
```

**Выгоды**:
- Устранение дублирования
- Единый источник truth для comment syntax

---

## 4. Потенциальные баги

### 4.1 Unsafe string slicing в delimiter detection (Высокий приоритет)

**Проблема**: Множество функций делают slicing без проверки границ.

**Примеры**:
```python
# rust/literals.py
def _detect_raw_string_closing(text: str) -> str:
    stripped = text.strip()
    match = re.match(r'^(r#+)"', stripped)
    if match:
        hash_count = len(match.group(1)) - 1
        return '"' + '#' * hash_count  # Корректно
    return '"'

# cpp/literals.py
def _detect_cpp_string_closing(text: str) -> str:
    stripped = text.strip()
    match = re.match(r'^R"([^(]*)\(', stripped)
    if match:
        delimiter = match.group(1)
        return f'){delimiter}"'  # Корректно

    if stripped.endswith("'"):
        return "'"
    return '"'

# НО! В других местах:
def _extract_content(self, text: str, opening: str, closing: str, wrapper: Optional[str] = None) -> Optional[str]:
    # ...
    if not stripped.startswith(opening) or not stripped.endswith(closing):
        return None

    return stripped[len(opening):-len(closing)]  # ОПАСНО! Если closing = "", будет stripped[len(opening):]
```

**Проблема**: Если `closing = ""`, то `stripped[len(opening):-0]` вернет пустую строку вместо `stripped[len(opening):]`.

**Рекомендация**: Добавить защиту:

```python
# processing/parser.py
def _extract_content(
    self,
    text: str,
    opening: str,
    closing: str,
    wrapper: Optional[str] = None
) -> Optional[str]:
    stripped = text.strip()

    # ... (wrapper handling)

    if not stripped.startswith(opening):
        return None

    # Безопасная проверка closing
    if closing and not stripped.endswith(closing):
        return None

    # Безопасный slicing
    start_pos = len(opening)
    end_pos = len(stripped) - len(closing) if closing else len(stripped)

    if start_pos >= end_pos:
        return None  # Пустой content

    return stripped[start_pos:end_pos]
```

**Выгоды**:
- Защита от edge cases с пустыми delimiters
- Явная обработка граничных условий

---

### 4.2 Missing validation для interpolation_markers (Низкий приоритет)

**Проблема**: В `InterpolationHandler.get_active_markers()` нет валидации структуры markers.

**Потенциальный баг**:
```python
# Если в дескрипторе ошибка:
BROKEN_STRING_PROFILE = StringProfile(
    # ...
    interpolation_markers=[
        ("$", "{", "}"),
        ("$",),  # НЕВАЛИДНЫЙ marker! Всего 1 элемент вместо 3
    ],
)

# В runtime:
def get_active_markers(self, profile: StringProfile, opening: str, content: str) -> List[Tuple[str, str, str]]:
    markers = profile.interpolation_markers
    if not markers:
        return []

    for marker in markers:
        prefix, opening_delim, closing_delim = marker  # ValueError: not enough values to unpack!
```

**Рекомендация**: Добавить валидацию (см. п. 1.2) + defensive programming:

```python
# utils/interpolation.py
def get_active_markers(
    self,
    profile: StringProfile,
    opening: str,
    content: str,
) -> List[Tuple[str, str, str]]:
    markers = profile.interpolation_markers
    if not markers:
        return []

    activation_callback = profile.interpolation_active
    active_markers = []

    for marker in markers:
        # Валидация структуры
        if not isinstance(marker, tuple) or len(marker) != 3:
            # Логировать warning и skip
            import logging
            logging.warning(
                f"Invalid interpolation marker in {profile.__class__.__name__}: {marker}. "
                f"Expected tuple of 3 elements (prefix, opening, closing). Skipping."
            )
            continue

        prefix, opening_delim, closing_delim = marker
        # ...
```

**Выгоды**:
- Graceful degradation вместо crash
- Раннее обнаружение конфигурационных ошибок

---

## 5. Code Style и консистентность

### 5.1 Inconsistent naming: `_get_parser_for_profile` vs `_create_element` (Низкий приоритет)

**Проблема**: Методы с префиксом `_get_` иногда создают объекты, иногда извлекают из кэша.

**Примеры**:
```python
# components/standard_collections.py
def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
    # Достает из кэша ИЛИ создает
    pass

# utils/element_parser.py
class ElementParser:
    def _create_element(self, text: str, raw_text: str, start: int, end: int) -> Element:
        # Всегда создает новый
        pass
```

**Рекомендация**: Унифицировать naming:
- `_get_*` — извлечение из кэша или существующих данных
- `_create_*` — создание нового объекта
- `_parse_*` — парсинг и создание структуры данных

```python
def _get_or_create_parser(self, profile: CollectionProfile) -> ElementParser:
    """Get cached parser or create new one."""
    pass

def _create_element(self, text: str, ...) -> Element:
    """Create new Element from parsed data."""
    pass

def _parse_content(self, content: str) -> List[Element]:
    """Parse content into list of elements."""
    pass
```

---

### 5.2 Verbose imports в language descriptors (Низкий приоритет)

**Проблема**: Каждый дескриптор дублирует длинный список imports.

**Пример**:
```python
# java/literals.py
from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    SequenceProfile,
    FactoryProfile,
    BlockInitProfile,
)

# kotlin/literals.py
from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    MappingProfile,
    FactoryProfile,
)

# 10 файлов × похожие imports
```

**Рекомендация**: Создать convenience import в `__init__.py`:

```python
# optimizations/literals/__init__.py
"""
Literal Optimization.

Convenience imports for language descriptor authors.
"""

# Re-export everything needed for descriptors
from .descriptor import LanguageLiteralDescriptor
from .patterns import (
    PlaceholderPosition,
    StringProfile,
    SequenceProfile,
    MappingProfile,
    FactoryProfile,
    BlockInitProfile,
)

__all__ = [
    # Descriptor
    "LanguageLiteralDescriptor",

    # Enums
    "PlaceholderPosition",

    # Profiles
    "StringProfile",
    "SequenceProfile",
    "MappingProfile",
    "FactoryProfile",
    "BlockInitProfile",
]

# Теперь в дескрипторах:
# java/literals.py
from ..optimizations import literals

JAVA_STRING_PROFILE = literals.StringProfile(
    query="...",
    opening="\"",
    closing="\"",
    placeholder_position=literals.PlaceholderPosition.INLINE,
    # ...
)
```

**Выгоды**:
- Короче imports
- Единая точка входа для авторов дескрипторов
- Легче добавлять новые паттерны

---

## 6. Тестирование

### 6.1 Отсутствие unit-тестов для utils (Средний приоритет)

**Проблема**: Утилитные модули (`interpolation.py`, `element_parser.py`, `indentation.py`) не покрыты unit-тестами.

**Риски**:
- Баги в утилитах ломают все языки
- Сложно рефакторить без уверенности в корректности
- Edge cases не проверяются

**Рекомендация**: Добавить unit-тесты:

```python
# tests/adapters/test_interpolation.py
import pytest
from lg.adapters.optimizations.literals.utils import InterpolationHandler

class TestInterpolationHandler:
    def test_find_interpolation_regions_simple(self):
        handler = InterpolationHandler()
        content = "Hello ${name}, you are ${age} years old"
        markers = [("$", "{", "}")]

        regions = handler.find_interpolation_regions(content, markers)

        assert regions == [(6, 13), (24, 30)]

    def test_find_interpolation_regions_nested(self):
        handler = InterpolationHandler()
        content = "${outer ${inner} more}"
        markers = [("$", "{", "}")]

        regions = handler.find_interpolation_regions(content, markers)

        # Должен найти outer, не ломаться на nested
        assert len(regions) == 1
        assert regions[0] == (0, 23)

    def test_adjust_truncation_at_boundary(self):
        handler = InterpolationHandler()
        original = "Hello ${name} world"
        truncated = "Hello $"  # Обрезано внутри interpolator
        markers = [("$", "{", "}")]

        adjusted = handler.adjust_truncation(truncated, original, markers)

        assert adjusted == "Hello ${name}"  # Расширено до полного interpolator

    # Больше тестов для edge cases...
```

**Покрытие**:
- `InterpolationHandler`: ~20 unit-тестов
- `ElementParser`: ~30 unit-тестов (parsing, nested structures, edge cases)
- `indentation`: ~10 unit-тестов

**Выгоды**:
- Высокая уверенность в корректности базовых утилит
- Возможность рефакторинга без страха
- Документация ожидаемого поведения через тесты

---

## 7. Приоритизация задач

### Высокий приоритет (сделать в первую очередь)

1. **1.1 Дублирование логики delimiter detection** — создать `DelimiterDetector`
2. **2.1 Избыточное создание ElementParser** — вынести `ElementParserFactory` в shared
3. **4.1 Unsafe string slicing** — добавить защиту границ

**Выгоды**: Устранение технического долга, снижение риска багов, улучшение производительности.

---

### Средний приоритет (следующая итерация)

4. **1.2 Отсутствие валидации профилей** — добавить `__post_init__` валидацию
5. **1.3 Неявная зависимость от порядка** — добавить priority и автосортировку
6. **2.2 Повторное вычисление factory_wrappers** — предвычислить при init
7. **3.1 Документация BlockInitProfile** — расширенные docstrings
8. **3.2 Поведение preserve_all_keys** — переименовать и документировать
9. **6.1 Unit-тесты для utils** — покрытие критичных утилит

**Выгоды**: Повышение maintainability, улучшение документации, снижение вероятности ошибок.

---

### Низкий приоритет (при наличии времени)

10. **2.3 Неэффективный поиск nested literals** — кэширование literal nodes
11. **3.3 Дублирование comment style** — переиспользовать `CommentFormatter`
12. **4.2 Валидация interpolation_markers** — defensive programming
13. **5.1 Inconsistent naming** — унификация `_get_*` vs `_create_*`
14. **5.2 Verbose imports** — convenience re-exports

**Выгоды**: Code polish, небольшие улучшения производительности, консистентность стиля.

---

## Итоговая оценка

**Сильные стороны**:
- ✅ Хорошая архитектурная основа (компоненты, shared сервисы, профили)
- ✅ Успешное покрытие 10 языков
- ✅ Единопроходная обработка
- ✅ DFS оптимизация для вложенных структур
- ✅ Типизированная ER-модель

**Слабые стороны**:
- ❌ Дублирование кода в language descriptors (delimiter detection)
- ❌ Отсутствие валидации конфигурации (профили)
- ❌ Некоторые проблемы производительности (повторное создание парсеров)
- ❌ Недостаточная документация сложных паттернов (BlockInitProfile)
- ❌ Слабое покрытие unit-тестами для utils

**Общая рекомендация**: Подсистема в хорошем состоянии, но требует рефакторинга для снижения дублирования и улучшения robustness. Приоритет — высокоприоритетные задачи (delimiter detector, parser factory, defensive slicing).

---

## Следующие шаги

1. Создать GitHub issues для высокоприоритетных задач
2. Реализовать `DelimiterDetector` и мигрировать все дескрипторы
3. Вынести `ElementParserFactory` в shared сервисы
4. Добавить валидацию профилей через `__post_init__`
5. Написать unit-тесты для критичных utils
6. Обновить документацию `literals_architecture.md` с учетом изменений

**Ожидаемый результат**: Снижение технического долга на ~60%, улучшение maintainability и robustness подсистемы.

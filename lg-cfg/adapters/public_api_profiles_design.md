# Public API Optimization: Profile-Based Architecture

## Overview

Profile-based architecture для public_api оптимизации заменяет императивные `_collect_*` методы в языковых адаптерах на декларативную систему профилей элементов.

**Статус**: Инфраструктура готова, 3 языка мигрированы (Scala, Java, Go)

---

## Why: Проблемы императивного подхода

Старый подход (до миграции):

```python
def collect_language_specific_private_elements(self) -> List[ElementInfo]:
    private_elements = []
    self._collect_traits(private_elements)
    self._collect_case_classes(private_elements)
    # ... еще 5-7 методов
    return private_elements

def _collect_traits(self, private_elements):
    traits = self.doc.query_opt("traits")
    seen_positions = set()  # Ручная дедупликация!
    for node, capture_name in traits:
        if capture_name == "trait_name":
            trait_def = node.parent
            # ... 15 строк логики
```

**Проблемы:**
- **Дублирование**: Каждый язык переписывает одну логику (200+ строк/язык)
- **Overlapping queries**: Tree-sitter queries возвращают дубликаты → нужна дедупликация
- **Хрупкость**: Легко забыть edge case или правильный parent node
- **Неправильный уровень захвата**: Query захватывает identifier, а удалять нужно весь declaration

---

## How: Архитектура

### Core Components

```
lg/adapters/optimizations/public_api/
├── profiles.py              # ElementProfile, LanguageElementProfiles
├── collector.py             # PublicApiCollector (универсальный)
└── language_profiles/
    ├── scala.py            # SCALA_PROFILES
    ├── java.py             # JAVA_PROFILES
    ├── go.py               # GO_PROFILES
    └── [другие языки]
```

### ElementProfile

```python
@dataclass
class ElementProfile:
    name: str                    # Имя для метрик ("class", "method", "field")
    query: str                   # Tree-sitter query (single-pattern!)

    # Optional hooks для специфичной логики
    parent_profile: Optional[str] = None
    additional_check: Optional[Callable] = None
    visibility_check: Optional[Callable] = None
    export_check: Optional[Callable] = None
    uses_visibility_for_public_api: bool = True
```

**Ключевой инсайт**: Query должен захватывать **весь declaration node**, не identifier:

```python
# ❌ WRONG - захватывает только identifier
query="(function_definition name: (identifier) @element)"

# ✅ CORRECT - захватывает весь declaration
query="(function_definition) @element"
```

### PublicApiCollector

Универсальный сборщик работает одинаково для всех языков:

```python
class PublicApiCollector:
    def collect_private_elements(self):
        private_elements = []
        for profile in self.profiles:
            elements = self._collect_by_profile(profile)
            private_elements.extend(elements)
        return self._filter_nested_elements(private_elements)  # Важно!
```

**Nested elements filter** - критический компонент: если класс приватный, не нужно отдельно удалять его поля (они удалятся автоматически).

---

## Language Profiles Examples

### Scala (простой случай)

```python
SCALA_PROFILES = LanguageElementProfiles(
    language="scala",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_definition) @element",
            additional_check=lambda node, doc: not is_case_class(node, doc)
        ),

        ElementProfile(
            name="method",
            query="(function_definition) @element",
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        # Abstract methods (no body) - отдельный профиль!
        ElementProfile(
            name="method",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: is_inside_class(node)
        ),
    ]
)
```

**Инсайт Scala**: Modifiers находятся прямо на declaration node, поэтому стандартная `CodeAnalyzer.determine_visibility()` работает без кастомизации.

### Go (custom visibility)

```python
GO_PROFILES = LanguageElementProfiles(
    language="go",
    profiles=[
        ElementProfile(
            name="struct",
            query="(type_declaration (type_spec type: (struct_type))) @element",
            visibility_check=lambda node, doc: _get_type_visibility(node, doc)
        ),

        ElementProfile(
            name="type",
            query="(type_declaration (type_alias)) @element",  # type Foo = Bar
            visibility_check=lambda node, doc: _get_type_visibility(node, doc)
        ),

        ElementProfile(
            name="type",
            query="(type_declaration (type_spec)) @element",   # type Foo Bar
            visibility_check=lambda node, doc: _get_type_visibility(node, doc),
            additional_check=lambda node, doc: not _has_struct_or_interface(node)
        ),
    ]
)

def _get_type_visibility(node: Node, doc: TreeSitterDocument) -> str:
    """Go visibility by naming: Uppercase = public, lowercase = private."""
    identifier = _find_type_identifier(node)
    name = doc.get_node_text(identifier)
    return "public" if name[0].isupper() else "private"
```

**Инсайты Go:**
- Type alias (`=`) и type definition (без `=`) - разные AST nodes
- Visibility определяется naming convention, нужен custom check
- Нужно искать identifier внутри declaration node

### Java (straightforward)

```python
JAVA_PROFILES = LanguageElementProfiles(
    language="java",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_declaration) @element"
        ),

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        # Top-level variables (Java tree-sitter quirk)
        ElementProfile(
            name="variable",
            query="(local_variable_declaration) @element",
            additional_check=lambda node, doc: not is_inside_method_or_constructor(node)
        ),
    ]
)
```

**Инсайт Java**: Top-level variables парсятся как `local_variable_declaration`, нужна проверка что не внутри метода.

---

## Integration

### CodeAnalyzer

```python
class CodeAnalyzer(ABC):
    def collect_private_elements_for_public_api(self):
        profiles = self.get_element_profiles()

        if profiles:
            # New path: via profiles
            collector = PublicApiCollector(self.doc, self, profiles)
            return collector.collect_private_elements()
        else:
            # Old path: legacy imperative methods
            return self._collect_private_elements_legacy()

    @abstractmethod
    def get_element_profiles(self):
        """Return LanguageElementProfiles or None (for legacy mode)."""
        pass
```

### Language Analyzer

```python
class ScalaCodeAnalyzer(CodeAnalyzer):
    def get_element_profiles(self):
        from ..optimizations.public_api.language_profiles.scala import SCALA_PROFILES
        return SCALA_PROFILES

    # Все _collect_* методы удалены - больше не нужны!
```

---

## Migration Status

### ✅ Completed Languages (48/48 tests)

| Language | Tests | Notes |
|----------|-------|-------|
| **Scala** | 5/5 | Modifiers на declaration node, нужны профили для function_declaration |
| **Java** | 5/5 | Field query должен захватывать field_declaration целиком |
| **Go** | 9/9 | Custom visibility check, type_alias vs type_spec distinction |
| **Python** | 7/7 | Simple visibility (underscore prefix), no custom checks needed |
| **TypeScript** | 6/6 | Semicolon extension via analyze_element(), namespace export checks |
| **JavaScript** | 6/6 | field_definition must be mapped in determine_element_type(), semicolon extension |
| **Rust** | 11/11 | Custom visibility (pub variants), trait methods inheritance, empty impl removal, top-level macros |
| **Kotlin** | 4/4 | Misparsed classes (infix_expression), custom decorator finding for annotated classes |

### 🔄 Pending Languages

- C/C++

---

## Key Lessons Learned

### 1. Query Granularity

**Всегда захватывайте declaration node, не identifier:**

```python
# ❌ Partial removal: "protected def foo()" → "def foo()"
query="(function_definition name: (identifier) @element)"

# ✅ Full removal: "protected def foo()" → "// … method omitted"
query="(function_definition) @element"
```

### 2. Nested Elements

**Обязательно фильтруйте вложенные элементы:**

```python
# Without filter: удаляются и класс, и все его поля отдельно
# → bad placeholders: "// … class omitted\n// … field omitted\n// … field omitted"

# With filter: удаляется только класс (поля внутри автоматически)
# → clean: "// … class omitted"
```

### 3. AST Node Types

**Разные концепты = разные AST nodes:**

- Scala: `function_definition` (с телом) vs `function_declaration` (abstract)
- Go: `type_alias` (`type A = B`) vs `type_spec` (`type A B`)
- Java: `field_declaration` vs `local_variable_declaration`

### 4. Visibility Logic

**Три подхода к visibility:**

1. **Standard** (Scala, Java, Python, TypeScript): modifiers/conventions на declaration node → стандартная логика работает
2. **Naming** (Go): по регистру имени → нужен custom `visibility_check`
3. **Export-based** (TypeScript namespaces): `export` keyword в контексте → нужен custom `export_check`

---

## TypeScript Migration: Lessons Learned

### Проблема 1: Semicolons в placeholders

**Симптом**: Placeholder показывает `// … field omitted;` вместо `// … field omitted`

**Причина**: Query захватывает только `public_field_definition`, без trailing semicolon. PlaceholderManager заменяет только declaration, semicolon остается.

**Решение**: Override `analyze_element()` в TypeScriptCodeAnalyzer для расширения range:

```python
def analyze_element(self, node: Node) -> ElementInfo:
    element_info = super().analyze_element(node)

    # Extend range for fields to include semicolon
    if element_info.element_type == "field":
        extended_node = self._extend_range_for_semicolon(node)
        element_info = ElementInfo(
            node=extended_node,
            # ... other fields
        )

    return element_info
```

**Урок**: Если язык требует специальной обработки ranges (semicolons, комментарии после), переопределяйте `analyze_element()`, не усложняйте профили.

---

### Проблема 2: Broken placeholder grouping

**Симптом**: Два соседних приватных поля создают два отдельных placeholder вместо одного "2 fields omitted"

**Причина**: Без расширения range на semicolon, PlaceholderManager видит разные ranges для соседних элементов:
- Field 1: `private field1: string` (без `;`)
- Semicolon: `;`
- Field 2: `private field2: number` (без `;`)

PlaceholderManager не может сгруппировать из-за content между элементами (semicolons).

**Решение**: То же самое - extend range to include semicolons в `analyze_element()`.

**Урок**: Группировка placeholders зависит от корректных ranges. Если элементы не группируются, проверьте что ranges включают все необходимое (punctuation, whitespace).

---

### Проблема 3: Protected members не удаляются

**Симптом**: `protected config: any = {}` остается в коде вместо placeholder

**Первоначальная ошибка**: Создал custom `visibility_check` который трактовал protected как public API в exported классах (логика наследования).

**Причина**: Неправильное понимание требований - комментарии в golden файле четко говорят "should be filtered out".

**Решение**: Удалил custom `visibility_check`, используется стандартная логика (protected = protected, удаляется).

**Урок**:
1. **Читайте golden files и комментарии в do-файлах** - они документируют ожидаемое поведение
2. **Не делайте assumptions** о том как "должно быть" (inheritance API) - следуйте существующей логике
3. **Начинайте с стандартной логики** - добавляйте custom checks только если явно нужно

---

### Проблема 4: Namespace members с некорректным export status

**Симптом**: Приватные функции внутри exported namespace считаются exported

**Причина**: Стандартная логика `determine_export_status()` ищет parent `export_statement`. Для namespace это дает:
```
export_statement
  └─ internal_module (namespace)
      └─ statement_block
          └─ function_declaration  # parent is export_statement!
```

**Решение**: Custom `export_check` для namespace members:

```python
def has_export_keyword(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if node has 'export' keyword directly."""
    node_text = doc.get_node_text(node).strip()
    if node_text.startswith("export "):
        return True
    if node.parent and node.parent.type == "export_statement":
        return True
    return False
```

**Урок**: Для вложенных структур (namespaces, modules) стандартная export логика не работает. Используйте `export_check` для точной проверки.

---

### Ошибки в процессе отладки

**Что делал неправильно:**
1. Много времени на debug logging вместо систематического сравнения с legacy code
2. Не изучил старую реализацию (`_collect_class_members()`) перед началом
3. Не использовал простые debug scripts - сразу пошел в heavy Golden infrastructure
4. Сделал assumptions (protected = public API) вместо чтения документации

**Что нужно было сделать:**
1. Прочитать `_collect_*` методы в старой реализации
2. Найти и понять все edge cases (semicolons, namespace exports)
3. Создать минимальные debug scripts для каждой проблемы
4. Проверить golden files и комментарии в do-файлах

**Правильный workflow:**
1. Изучить legacy implementation (старые `_collect_*` методы)
2. Найти все queries и их использование
3. Понять edge cases (semicolons, extended ranges, custom checks)
4. Написать профили следуя найденным паттернам
5. Debug scripts для быстрой итерации
6. Golden tests как финальная верификация

---

## Next Steps

### Immediate (остальные языки)

1. **JavaScript** - похож на TypeScript, export keyword
2. **Rust** - pub keyword logic
3. **C/C++** - static keyword
4. **Kotlin** - modifiers как Scala

### Strategy

Для каждого языка:

1. Изучить AST структуру (`debug_*_ast.py` script)
2. Написать профили с правильным уровнем захвата
3. Добавить custom visibility_check если нужно
4. Запустить тесты, исправить goldens
5. Удалить legacy `_collect_*` методы

### Phase 4: Cleanup

После миграции всех языков:

1. Удалить `_collect_private_elements_legacy()` из `CodeAnalyzer`
2. Удалить все старые `_collect_*` методы
3. Сделать `get_element_profiles()` required (без Optional)
4. Обновить документацию

---

## Benefits Achieved

### Code Reduction

- **До**: 200+ строк императивного кода в каждом языке
- **После**: 50-80 строк декларативных профилей

### Quality Improvements

- ✅ Нет дублирования логики
- ✅ Нет ручной дедупликации
- ✅ Правильный уровень удаления (весь declaration)
- ✅ Чистые placeholders (без вложенных дублей)

### Maintainability

- ✅ Добавить новый тип элемента = добавить профиль
- ✅ Центральная логика в одном месте (collector)
- ✅ Легко тестировать профили изолированно

---

## Common Patterns

### Pattern 1: Member vs Top-Level

```python
# Methods inside classes
ElementProfile(
    name="method",
    query="(function_definition) @element",
    additional_check=lambda node, doc: is_inside_class(node)
),

# Top-level functions
ElementProfile(
    name="function",
    query="(function_definition) @element",
    additional_check=lambda node, doc: not is_inside_class(node)
),
```

### Pattern 2: Multiple Queries for Same Type

```python
# Concrete methods
ElementProfile(name="method", query="(function_definition) @element"),

# Abstract methods
ElementProfile(name="method", query="(function_declaration) @element"),
```

### Pattern 3: Custom Visibility Extraction

```python
def _get_declaration_visibility(node: Node, doc: TreeSitterDocument, id_type: str):
    """Find identifier within declaration and check its case/modifiers."""
    identifier = _find_identifier(node, id_type)
    name = doc.get_node_text(identifier)
    # Language-specific logic here
    return "public" if condition else "private"
```

---

## Troubleshooting

### Issue: Elements not found (0 private elements)

**Причина**: Query не соответствует AST структуре

**Решение**: Написать `debug_*_ast.py` скрипт, проверить реальную структуру

### Issue: Partial removal (keyword остается)

**Причина**: Query захватывает identifier, не declaration

**Решение**: Изменить query на `(declaration_type) @element`

### Issue: Duplicate placeholders

**Причина**: Не работает nested elements filter

**Решение**: Проверить что `_filter_nested_elements()` вызывается в collector

### Issue: Wrong visibility determination

**Причина**: Standard logic не подходит для языка

**Решение**: Добавить custom `visibility_check` в профиль

---

## Files Reference

### Core Infrastructure

- `lg/adapters/optimizations/public_api/profiles.py` - ElementProfile, LanguageElementProfiles
- `lg/adapters/optimizations/public_api/collector.py` - PublicApiCollector, nested filter
- `lg/adapters/optimizations/public_api/optimizer.py` - PublicApiOptimizer (unchanged)
- `lg/adapters/code_analysis.py` - CodeAnalyzer с `get_element_profiles()` method

### Language Profiles

- `lg/adapters/optimizations/public_api/language_profiles/scala.py`
- `lg/adapters/optimizations/public_api/language_profiles/java.py`
- `lg/adapters/optimizations/public_api/language_profiles/go.py`

### Test Utils

- `tests/adapters/<lang>/test_public_api.py` - Golden tests
- `tests/adapters/<lang>/goldens/` - Golden files
- `scripts/test_adapters.sh` - Test runner

---

## Conclusion

Profile-based architecture успешно решает проблемы императивного подхода:

- **Декларативность** вместо 200+ строк кода
- **Переиспользование** через наследование профилей
- **Надежность** через правильный уровень захвата
- **Масштабируемость** на любое количество языков

Миграция 3 языков доказала жизнеспособность архитектуры. Оставшиеся языки мигрируются по тому же паттерну.

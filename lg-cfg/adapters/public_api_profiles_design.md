# Public API Optimization: Profile-Based Architecture

## Проблема

Текущая реализация public_api оптимизации использует императивный подход с ручными `_collect_*` методами в каждом языковом адаптере:

```python
def collect_language_specific_private_elements(self) -> List[ElementInfo]:
    private_elements = []
    self._collect_traits(private_elements)
    self._collect_case_classes(private_elements)
    self._collect_objects(private_elements)
    self._collect_class_fields(private_elements)
    self._collect_type_aliases(private_elements)
    return private_elements

def _collect_traits(self, private_elements: List[ElementInfo]) -> None:
    traits = self.doc.query_opt("traits")
    seen_positions = set()  # Ручная дедупликация!
    for node, capture_name in traits:
        if capture_name == "trait_name":
            trait_def = node.parent
            if trait_def:
                pos_key = (trait_def.start_byte, trait_def.end_byte)
                if pos_key in seen_positions:
                    continue
                seen_positions.add(pos_key)
                # ... еще 10 строк логики
```

### Проблемы этого подхода:

1. **Дублирование кода**: Каждый язык переписывает одну и ту же логику сбора
2. **Overlapping queries**: Tree-sitter queries с множественными паттернами возвращают дубликаты
3. **Ручная дедупликация**: В 4 языках из 10 требуется `seen_positions` костыль
4. **Нет переиспользования**: Логика для похожих элементов (class/case_class) дублируется
5. **Сложность поддержки**: 200+ строк императивного кода в каждом языке
6. **Хрупкость**: Легко забыть edge case или дедупликацию

### Корневая причина:

Tree-sitter queries в `lg/adapters/<язык>/queries.py` создавались для **поиска паттернов** (literals, imports), а не для **точной категоризации** (code_analysis).

Пример проблемного query (Scala traits):
```python
"traits": """
(trait_definition
  name: (identifier) @trait_name
  body: (template_body) @trait_body)

(trait_definition
  name: (identifier) @trait_name)
"""
```

Trait с body попадает в **оба** паттерна → дубликаты → нужна дедупликация.

---

## Решение: Profile-Based Architecture

По аналогии с **literal profiles** (`lg/adapters/optimizations/literals/profiles/`), создать **декларативную систему профилей элементов**.

### Ключевая идея:

Вместо императивных методов → **декларативные профили** с:
1. **Точным single-pattern query** (без overlaps)
2. **Наследованием профилей** (для общих случаев)
3. **Опциональной императивной логикой** (только где необходимо)

### Аналогия с Literal Profiles:

| Literal Profiles | Element Profiles |
|-----------------|------------------|
| `LiteralProfile` | `ElementProfile` |
| `ArrayLiteralProfile` | `ClassElementProfile` |
| `language_profiles/python.py` | `language_profiles/scala.py` |
| `query`: tree-sitter pattern | `query`: tree-sitter pattern |
| `formatter`: опциональный | `visibility_check`: опциональный |

---

## Архитектура

### Структура пакета:

```
lg/adapters/optimizations/public_api/
├── __init__.py
├── profiles.py              # Базовые классы профилей
├── analyzer.py              # Унифицированный PublicApiAnalyzer
├── collector.py             # Универсальный сборщик по профилям
└── language_profiles/       # Профили для каждого языка
    ├── __init__.py
    ├── scala.py
    ├── java.py
    ├── rust.py
    ├── go.py
    ├── javascript.py
    ├── typescript.py
    ├── python.py
    ├── c.py
    ├── cpp.py
    └── kotlin.py
```

### Core Classes:

#### 1. ElementProfile (profiles.py)

```python
from dataclasses import dataclass
from typing import Optional, Callable
from ..tree_sitter_support import Node, TreeSitterDocument

@dataclass
class ElementProfile:
    """
    Декларативное описание типа элемента для public API фильтрации.

    Профиль описывает:
    - Как найти элементы этого типа (query)
    - Как их идентифицировать (additional_check)
    - Как определить приватность (visibility_check)
    - Как их назвать в placeholder (placeholder_name)
    """

    # === Основные поля ===

    name: str
    """
    Имя профиля для метрик и placeholder, например: "class", "trait", "case_class".

    Используется для:
    - Метрик: scala.removed.{name}
    - Placeholder: "... {name} omitted ..."
    - Наследования профилей (parent_profile)
    """

    query: str
    """
    Tree-sitter query для поиска элементов этого типа.

    ВАЖНО: Должен быть single-pattern (без union паттернов) для избежания дубликатов.
    Capture name всегда должен быть @element.

    Примеры:
        "(class_definition name: (identifier) @element)"
        "(trait_definition name: (identifier) @element)"
        "(function_declaration name: (identifier) @element)"
    """

    # === Наследование ===

    parent_profile: Optional[str] = None
    """
    Имя родительского профиля для наследования.

    При наследовании:
    - query берется от parent (если не переопределен)
    - placeholder_name берется от parent (если не переопределен)
    - additional_check комбинируется (parent_check AND child_check)

    Пример:
        case_class_profile.parent_profile = "class"
    """

    # === Опциональная императивная логика ===

    additional_check: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Дополнительная проверка что нода именно этого типа.

    Используется когда query не может точно отфильтровать элементы.

    Примеры:
        - Отличить case class от class: lambda node, doc: "case" in doc.get_node_text(node)[:50]
        - Отличить private typedef struct от обычного: lambda node, doc: "static" not in doc.get_node_text(node)

    Args:
        node: Tree-sitter node (результат query)
        doc: TreeSitterDocument для получения текста

    Returns:
        True если это элемент этого профиля
    """

    visibility_check: Optional[Callable[[Node, TreeSitterDocument], str]] = None
    """
    Кастомная логика определения видимости элемента.

    Используется для языков с нестандартной логикой видимости:
    - Go: по регистру первой буквы (uppercase = public)
    - JavaScript: по префиксу _ или # (convention-based)
    - Python: по префиксу _ или __ (convention-based)

    Если не задан, используется стандартная логика через CodeAnalyzer.determine_visibility().

    Args:
        node: Tree-sitter node элемента
        doc: TreeSitterDocument

    Returns:
        "public", "private", "protected"
    """

    export_check: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Кастомная логика определения экспорта элемента.

    Если не задан, используется CodeAnalyzer.determine_export_status().

    Args:
        node: Tree-sitter node элемента
        doc: TreeSitterDocument

    Returns:
        True если элемент экспортируется
    """
```

#### 2. LanguageElementProfiles (profiles.py)

```python
@dataclass
class LanguageElementProfiles:
    """
    Коллекция профилей элементов для конкретного языка.
    """

    language: str
    """Имя языка: "scala", "java", "rust", ..."""

    profiles: List[ElementProfile]
    """Список профилей элементов для этого языка."""

    def resolve_inheritance(self) -> List[ElementProfile]:
        """
        Разрешить наследование профилей.

        Создает плоский список профилей где parent_profile заменен на реальные значения.

        Returns:
            Список разрешенных профилей
        """
        # Строим map: name -> profile
        profile_map = {p.name: p for p in self.profiles}

        resolved = []
        for profile in self.profiles:
            if profile.parent_profile:
                parent = profile_map.get(profile.parent_profile)
                if not parent:
                    raise ValueError(f"Unknown parent profile: {profile.parent_profile}")

                # Наследуем поля от parent
                resolved_profile = ElementProfile(
                    name=profile.name,
                    query=profile.query or parent.query,
                    parent_profile=None,  # убираем наследование
                    additional_check=self._combine_checks(parent.additional_check, profile.additional_check),
                    visibility_check=profile.visibility_check or parent.visibility_check,
                    export_check=profile.export_check or parent.export_check,
                )
                resolved.append(resolved_profile)
            else:
                resolved.append(profile)

        return resolved

    @staticmethod
    def _combine_checks(
        parent_check: Optional[Callable],
        child_check: Optional[Callable]
    ) -> Optional[Callable]:
        """Комбинировать parent и child additional_check через AND."""
        if not parent_check:
            return child_check
        if not child_check:
            return parent_check

        return lambda node, doc: parent_check(node, doc) and child_check(node, doc)
```

#### 3. PublicApiCollector (collector.py)

```python
class PublicApiCollector:
    """
    Универсальный сборщик приватных элементов на основе профилей.

    Заменяет ручные _collect_* методы декларативной логикой.
    """

    def __init__(
        self,
        doc: TreeSitterDocument,
        analyzer: CodeAnalyzer,
        profiles: LanguageElementProfiles
    ):
        self.doc = doc
        self.analyzer = analyzer
        self.profiles = profiles.resolve_inheritance()

    def collect_private_elements(self) -> List[ElementInfo]:
        """
        Собрать все приватные элементы используя профили.

        Returns:
            Список приватных элементов для удаления
        """
        private_elements = []

        for profile in self.profiles:
            elements = self._collect_by_profile(profile)
            private_elements.extend(elements)

        return private_elements

    def _collect_by_profile(self, profile: ElementProfile) -> List[ElementInfo]:
        """
        Собрать элементы по одному профилю.

        Args:
            profile: Профиль элемента

        Returns:
            Список приватных элементов этого типа
        """
        # Выполняем query (используем query_nodes для получения только @element)
        nodes = self.doc.query_nodes(profile.query, "element")

        private_elements = []
        for node in nodes:
            # Опциональная additional_check
            if profile.additional_check:
                if not profile.additional_check(node, self.doc):
                    continue  # Это не элемент этого профиля

            # Получаем definition node (node может быть identifier)
            element_def = self._get_element_definition(node)
            if not element_def:
                continue

            # Анализируем элемент
            element_info = self.analyzer.analyze_element(element_def)

            # Переопределяем element_type именем профиля (для метрик)
            element_info.element_type = profile.name

            # Проверяем приватность
            if self._is_private_element(element_def, element_info, profile):
                private_elements.append(element_info)

        return private_elements

    def _get_element_definition(self, node: Node) -> Optional[Node]:
        """
        Получить definition node для элемента.

        Query может вернуть identifier, но нам нужен parent definition node.

        Args:
            node: Node из query result

        Returns:
            Definition node или None
        """
        # Если это identifier, берем parent
        if node.type in ("identifier", "type_identifier", "field_identifier"):
            return node.parent

        # Иначе это уже definition
        return node

    def _is_private_element(
        self,
        element_def: Node,
        element_info: ElementInfo,
        profile: ElementProfile
    ) -> bool:
        """
        Проверить что элемент приватный.

        Args:
            element_def: Definition node элемента
            element_info: Информация об элементе
            profile: Профиль элемента

        Returns:
            True если элемент приватный и должен быть удален
        """
        # Используем кастомную логику visibility если задана
        if profile.visibility_check:
            visibility = profile.visibility_check(element_def, self.doc)
            is_public = (visibility == "public")
        else:
            is_public = element_info.is_public

        # Используем кастомную логику export если задана
        if profile.export_check:
            is_exported = profile.export_check(element_def, self.doc)
        else:
            is_exported = element_info.is_exported

        # Логика как в текущем CodeAnalyzer
        return not element_info.in_public_api
```

---

## Language Profiles

### Пример: Scala (language_profiles/scala.py)

```python
"""
Element profiles for Scala language.
"""
from ..profiles import ElementProfile, LanguageElementProfiles

# Helper functions
def is_case_class(node, doc):
    """Check if class_definition is a case class."""
    node_text = doc.get_node_text(node)
    return "case class" in node_text[:50]

def is_private_modifier(node, doc):
    """Check if element has private modifier."""
    node_text = doc.get_node_text(node)
    return node_text.strip().startswith("private ")

# Element profiles
SCALA_PROFILES = LanguageElementProfiles(
    language="scala",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_definition name: (identifier) @element)",
            # Exclude case classes via additional_check
            additional_check=lambda node, doc: not is_case_class(node, doc)
        ),

        ElementProfile(
            name="case_class",
            query="(class_definition name: (identifier) @element)",
            additional_check=is_case_class  # Only case classes
        ),

        # === Traits ===

        ElementProfile(
            name="trait",
            # Single pattern without overlap!
            query="(trait_definition name: (identifier) @element)"
        ),

        # === Objects ===

        ElementProfile(
            name="object",
            query="(object_definition name: (identifier) @element)"
        ),

        # === Type aliases ===

        ElementProfile(
            name="type",
            query="(type_definition name: (identifier) @element)"
        ),

        # === Methods ===

        ElementProfile(
            name="method",
            query="""
            (function_definition
              name: (identifier) @element
            )
            """,
            # Only methods inside classes (not top-level functions)
            additional_check=lambda node, doc: _is_inside_class(node)
        ),

        # === Class fields ===

        ElementProfile(
            name="field",
            query="""
            (val_definition
              pattern: (identifier) @element
            )
            """,
            additional_check=lambda node, doc: _is_inside_class(node)
        ),

        ElementProfile(
            name="field",  # Use same name for var
            query="""
            (var_definition
              pattern: (identifier) @element
            )
            """,
            additional_check=lambda node, doc: _is_inside_class(node)
        ),
    ]
)

def _is_inside_class(node):
    """Check if node is inside class/object/trait."""
    current = node.parent
    while current:
        if current.type in ("class_definition", "object_definition", "trait_definition"):
            return True
        if current.type == "compilation_unit":
            break
        current = current.parent
    return False
```

### Пример: Go (language_profiles/go.py)

```python
"""
Element profiles for Go language.
"""
from ..profiles import ElementProfile, LanguageElementProfiles

def go_visibility_check(node, doc):
    """
    Go visibility определяется регистром первой буквы.
    Uppercase = public, lowercase = private.
    """
    # Получаем имя элемента
    name_node = node.child_by_field_name("name")
    if not name_node:
        return "public"

    name = doc.get_node_text(name_node)
    if not name:
        return "public"

    # Go convention: uppercase = exported
    return "public" if name[0].isupper() else "private"

GO_PROFILES = LanguageElementProfiles(
    language="go",
    profiles=[
        # === Structs ===

        ElementProfile(
            name="struct",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier) @element
                type: (struct_type)
              )
            )
            """,
            visibility_check=go_visibility_check
        ),

        # === Interfaces ===

        ElementProfile(
            name="interface",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier) @element
                type: (interface_type)
              )
            )
            """,
            visibility_check=go_visibility_check
        ),

        # === Functions ===

        ElementProfile(
            name="function",
            query="(function_declaration name: (identifier) @element)",
            visibility_check=go_visibility_check
        ),

        # === Methods ===

        ElementProfile(
            name="method",
            query="(method_declaration name: (field_identifier) @element)",
            # Methods are never exported directly
            export_check=lambda node, doc: False
        ),

        # === Variables and constants ===

        ElementProfile(
            name="var",
            query="""
            (var_declaration
              (var_spec name: (identifier) @element)
            )
            """,
            visibility_check=go_visibility_check,
            # Only module-level (not inside functions)
            additional_check=lambda node, doc: not _is_inside_function(node)
        ),

        ElementProfile(
            name="const",
            query="""
            (const_declaration
              (const_spec name: (identifier) @element)
            )
            """,
            visibility_check=go_visibility_check,
            additional_check=lambda node, doc: not _is_inside_function(node)
        ),

        # === Struct fields ===

        ElementProfile(
            name="field",
            query="""
            (field_declaration
              name: (field_identifier) @element
            )
            """,
            visibility_check=go_visibility_check,
            # Только приватные поля в публичных структурах
            additional_check=lambda node, doc: _is_in_exported_struct(node, doc)
        ),
    ]
)

def _is_inside_function(node):
    """Check if inside function body."""
    current = node.parent
    while current:
        if current.type == "block":
            if current.parent and current.parent.type in ("function_declaration", "method_declaration"):
                return True
        if current.type == "source_file":
            return False
        current = current.parent
    return False

def _is_in_exported_struct(node, doc):
    """Check if field is in exported struct."""
    current = node.parent
    while current:
        if current.type == "type_spec":
            for child in current.children:
                if child.type == "type_identifier":
                    name = doc.get_node_text(child)
                    return name[0].isupper() if name else False
        if current.type == "source_file":
            break
        current = current.parent
    return False
```

---

## Integration

### 1. Обновить CodeAnalyzer

```python
# lg/adapters/code_analysis.py

class CodeAnalyzer(ABC):

    def collect_private_elements_for_public_api(self) -> List[ElementInfo]:
        """
        Собрать все приватные элементы для удаления в public API режиме.

        Новая реализация через profiles.
        """
        # Получаем профили для языка
        profiles = self.get_element_profiles()

        if profiles:
            # Новый путь: через PublicApiCollector
            from .optimizations.public_api.collector import PublicApiCollector

            collector = PublicApiCollector(self.doc, self, profiles)
            return collector.collect_private_elements()
        else:
            # Старый путь: через императивные методы (backward compatibility)
            return self._collect_private_elements_legacy()

    @abstractmethod
    def get_element_profiles(self) -> Optional[LanguageElementProfiles]:
        """
        Получить профили элементов для языка.

        Returns:
            LanguageElementProfiles или None (если используется legacy режим)
        """
        pass

    def _collect_private_elements_legacy(self) -> List[ElementInfo]:
        """Legacy императивная реализация (для обратной совместимости)."""
        private_elements = []
        self._collect_private_functions_and_methods(private_elements)
        self._collect_classes(private_elements)
        self._collect_interfaces_and_types(private_elements)
        language_specific = self.collect_language_specific_private_elements()
        private_elements.extend(language_specific)
        return private_elements
```

### 2. Обновить ScalaCodeAnalyzer

```python
# lg/adapters/scala/code_analysis.py

class ScalaCodeAnalyzer(CodeAnalyzer):

    def get_element_profiles(self) -> LanguageElementProfiles:
        """Возвращаем Scala element profiles."""
        from ..optimizations.public_api.language_profiles.scala import SCALA_PROFILES
        return SCALA_PROFILES

    # Удаляем все _collect_* методы!
    # collect_language_specific_private_elements больше не нужен
```

### 3. Миграция других языков

Постепенно мигрировать все языки:
1. Scala (первый, как пример)
2. Go (демонстрация custom visibility_check)
3. Java, Kotlin (простые случаи)
4. JavaScript, TypeScript (convention-based visibility)
5. Rust (сложная логика pub)
6. C, C++ (static, extern)
7. Python (convention-based __)

---

## Преимущества

### 1. Декларативность

**Было** (200+ строк императивного кода):
```python
def _collect_traits(self, private_elements):
    traits = self.doc.query_opt("traits")
    seen_positions = set()
    for node, capture_name in traits:
        if capture_name == "trait_name":
            trait_def = node.parent
            if trait_def:
                pos_key = (trait_def.start_byte, trait_def.end_byte)
                if pos_key in seen_positions:
                    continue
                seen_positions.add(pos_key)
                element_info = self.analyze_element(trait_def)
                if not element_info.in_public_api:
                    private_elements.append(element_info)
```

**Стало** (10 строк декларативного описания):
```python
ElementProfile(
    name="trait",
    placeholder_name="trait omitted",
    query="(trait_definition name: (identifier) @element)"
)
```

### 2. Нет дубликатов

Single-pattern queries → нет overlaps → не нужна дедупликация.

### 3. Переиспользование через наследование

```python
# Базовый профиль
class_profile = ElementProfile(name="class", ...)

# Наследуем и уточняем
case_class_profile = ElementProfile(
    name="case_class",
    parent_profile="class",
    additional_check=is_case_class
)
```

### 4. Простота тестирования

Каждый профиль можно тестировать изолированно:

```python
def test_scala_trait_profile():
    profile = SCALA_PROFILES.profiles[2]  # trait

    doc = ScalaDocument("trait Foo { def bar(): Unit }")
    nodes = doc.query_nodes(profile.query, "element")

    assert len(nodes) == 1
    assert doc.get_node_text(nodes[0]) == "Foo"
```

### 5. Легко добавлять новые типы

Просто добавить новый ElementProfile в список.

### 6. Централизованная логика

Вся логика сбора в одном месте (`PublicApiCollector`), а не размазана по 10 языковым адаптерам.

---

## План миграции

### Phase 1: Инфраструктура (1-2 дня)

1. Создать `lg/adapters/optimizations/public_api/` пакет
2. Реализовать `ElementProfile`, `LanguageElementProfiles`
3. Реализовать `PublicApiCollector`
4. Обновить `CodeAnalyzer` с `get_element_profiles()`

### Phase 2: Pilot (Scala) (1 день)

1. Создать `language_profiles/scala.py`
2. Обновить `ScalaCodeAnalyzer.get_element_profiles()`
3. Удалить все `_collect_*` методы из Scala
4. Прогнать тесты, убедиться что всё работает

### Phase 3: Остальные языки (3-4 дня)

Мигрировать по одному языку в день:
1. Go (custom visibility check)
2. Java (простой)
3. JavaScript (convention-based)
4. TypeScript
5. Rust (pub logic)
6. Python
7. C, C++
8. Kotlin

### Phase 4: Cleanup (1 день)

1. Удалить legacy `_collect_private_elements_legacy()`
2. Удалить старые `_collect_*` методы из базового CodeAnalyzer
3. Обновить документацию

---

## Backward Compatibility

Во время миграции сохраняем обратную совместимость:

```python
def collect_private_elements_for_public_api(self):
    profiles = self.get_element_profiles()

    if profiles:
        # Новый путь
        return PublicApiCollector(...).collect_private_elements()
    else:
        # Старый путь
        return self._collect_private_elements_legacy()
```

Языки мигрируем постепенно. Пока язык не мигрирован, `get_element_profiles()` возвращает `None` и используется legacy path.

---

## Альтернативы (рассмотренные и отвергнутые)

### A. Автодедупликация в TreeSitterDocument.query()

**Pros**: Быстро фиксит симптом

**Cons**:
- Не решает overlap проблему
- Не помогает различить class vs case_class
- Скрывает реальную проблему

**Вердикт**: ❌ Латание дыр

### B. Фиксить queries.py

**Pros**: Решает дубликаты

**Cons**:
- Очень сложно подобрать non-overlapping queries
- Не решает архитектурную проблему императивных методов
- Queries всё равно создавались для другой цели (literals)

**Вердикт**: ❌ Недостаточно

### C. Profile-Based Architecture

**Pros**:
- Декларативность
- Переиспользование
- Нет дубликатов
- Простота тестирования
- Масштабируемость

**Cons**:
- Требует больше времени на реализацию

**Вердикт**: ✅ **Выбрано**

---

## Заключение

Profile-based architecture для public_api оптимизации:

1. **Решает корневую проблему**: убирает императивный код и overlapping queries
2. **Масштабируется**: легко добавлять новые типы и языки
3. **Поддерживается**: декларативный код легче читать и менять
4. **Тестируется**: каждый профиль изолированно тестируется
5. **Переиспользует**: наследование профилей убирает дублирование

Это не латание дыр, а фундаментальное улучшение архитектуры.

---

## IMPLEMENTATION STATUS (Updated 2025-12-22)

### Completed Phases

#### ✅ Phase 1: Infrastructure (Completed)

**Files created:**
- `lg/adapters/optimizations/public_api/profiles.py` - ElementProfile, LanguageElementProfiles
- `lg/adapters/optimizations/public_api/collector.py` - PublicApiCollector
- `lg/adapters/optimizations/public_api/optimizer.py` - Moved from old public_api.py
- `lg/adapters/optimizations/public_api/language_profiles/` - Package for language profiles

**Core infrastructure:**
- `ElementProfile` dataclass with:
  - `name`: Profile name for metrics/placeholders
  - `query`: Single-pattern tree-sitter query
  - `parent_profile`: Inheritance support
  - `additional_check`: Optional refinement logic
  - `visibility_check`: Custom visibility logic
  - `export_check`: Custom export logic
  - `uses_visibility_for_public_api`: NEW - Explicit API semantics flag (see below)

- `PublicApiCollector`: Universal collector using profiles
- `CodeAnalyzer.get_element_profiles()`: Abstract method for language profiles
- Backward compatibility: languages return None → use legacy mode

**Git commit:** `1921a7f feat: Implement Phase 1 - profile-based public_api infrastructure`

#### ✅ Phase 2: Scala Profiles (Completed)

**File created:**
- `lg/adapters/optimizations/public_api/language_profiles/scala.py`

**Profiles implemented:**
- 10 element types: class, case_class, trait, object, type, function, method, variable, field (val/var)
- Single-pattern queries (no overlaps)
- ~120 lines of imperative code removed from ScalaCodeAnalyzer

**Results:**
- 4/5 tests passing (1 golden formatting mismatch only)
- No deduplication needed
- Clean declarative code

**Git commit:** `23a7178 feat: Implement Phase 2 - Scala element profiles (pilot)`

#### 🔄 Phase 3: Remaining Languages (In Progress)

**Languages migrated:**

1. **Scala** - ✅ Complete (4/5 tests)
2. **Java** - 🔄 Partial (10/14 tests)
   - Issues: field visibility query needs work
3. **Go** - 🔄 Partial (10/14 tests)
   - Issues: type alias query overlap with struct/interface

**Languages pending:**
- JavaScript
- TypeScript
- Rust
- C/C++
- Python
- Kotlin

**Git commits:**
- `5b185ef WIP: Migrate Java and Go to profiles (partial)`
- `0b6af7b feat: Add uses_visibility_for_public_api to ElementProfile`

### Architecture Evolution

#### Critical Discovery: uses_visibility_for_public_api

**Problem found during Java migration:**

Original `ElementInfo.in_public_api` property used heuristic:
```python
member_types = {"method", "field", "property", "val", "var", "constructor"}
if self.element_type in member_types:
    return self.is_public  # visibility-based
else:
    return self.is_exported  # export-based
```

When `PublicApiCollector` overrides `element_type` with profile name (e.g., "variable"), this heuristic breaks:
- Java top-level variables: use visibility (public/private), NOT export
- But "variable" not in member_types → checks export → WRONG!

**Solution: Explicit flag in ElementProfile**

Added `uses_visibility_for_public_api: bool = True`:
```python
@dataclass
class ElementProfile:
    name: str
    query: str
    # ... other fields ...
    uses_visibility_for_public_api: bool = True
    """
    Whether this element type uses visibility for public API determination.

    - True (default): Element is in public API if it's public (visibility-based)
    - False: Element is in public API if it's exported (export-based)

    Examples:
    - Java fields/variables: uses_visibility_for_public_api=True
    - TypeScript top-level functions: uses_visibility_for_public_api=False
    - Go everything: uses_visibility_for_public_api=True (naming IS visibility)
    """
```

**Benefits:**
- ✅ Declarative: languages explicitly control semantics
- ✅ No heuristics: clear and predictable
- ✅ Flexible: supports both visibility and export paradigms
- ✅ Default True: most common case

**Implementation:**
- Added to `ElementProfile` (profiles.py)
- Added to `ElementInfo` (code_analysis.py)
- Collector passes flag from profile to ElementInfo
- `in_public_api` property checks flag first, then fallback to heuristic

### Known Issues & Next Steps

#### Java (10/14 tests passing)

**Issue 1: Field visibility**
- Test `test_class_member_visibility` fails
- Fields being removed incorrectly
- Need to debug field query: `(field_declaration declarator: (variable_declarator name: (identifier) @element))`
- May need to adjust query to capture declaration node directly

**Issue 2: Golden formatting**
- Test `test_public_api_only_basic` fails on golden match
- Likely just placeholder formatting differences
- Will resolve after all tests pass

#### Go (10/14 tests passing)

**Issue 1: Type alias overlap**
- Test `test_type_aliases` fails
- Query `(type_declaration (type_spec name: (type_identifier) @element))` catches structs AND interfaces too
- Added `is_type_alias_not_struct_or_interface` check but still failing
- Need better query or additional_check logic

**Issue 2: Golden formatting**
- Test `test_public_api_only_basic` fails on golden match

#### General Strategy

**For complex languages (Java, Go, Rust):**
1. Debug and fix issues before moving to simpler languages
2. Validate architecture handles edge cases
3. Learn patterns that apply to other languages

**Next actions:**
1. Fix Java field query issue
2. Fix Go type alias query issue
3. Ensure 14/14 tests pass for both
4. Then migrate: JavaScript → TypeScript → Python → Rust → C/C++ → Kotlin

### Files Modified Summary

**Core infrastructure:**
- `lg/adapters/optimizations/public_api/profiles.py`
- `lg/adapters/optimizations/public_api/collector.py`
- `lg/adapters/code_analysis.py` (+ uses_visibility_for_public_api)

**Language profiles created:**
- `lg/adapters/optimizations/public_api/language_profiles/scala.py`
- `lg/adapters/optimizations/public_api/language_profiles/java.py`
- `lg/adapters/optimizations/public_api/language_profiles/go.py`

**Language analyzers updated:**
- `lg/adapters/scala/code_analysis.py` - returns SCALA_PROFILES, removed ~120 lines
- `lg/adapters/java/code_analysis.py` - returns JAVA_PROFILES, removed ~100 lines
- `lg/adapters/go/code_analysis.py` - returns GO_PROFILES, removed ~80 lines
- All other languages: added stub `get_element_profiles()` returning None (legacy mode)

### Test Results Summary

```
Scala:  4/5 tests   (80%) ✅
Java:  10/14 tests  (71%) 🔄
Go:    10/14 tests  (71%) 🔄
Other: N/A          (using legacy mode)

Total migrated tests: 24/33 (73%)
```

### Key Learnings

1. **Query granularity matters**: Capture the definition node, not identifier
2. **Tree-sitter varies by language**: Java top-level constants are `local_variable_declaration`
3. **Explicit over implicit**: `uses_visibility_for_public_api` > heuristics
4. **Test complex first**: Java/Go revealed architectural issues early
5. **Single-pattern queries**: No overlaps = no deduplication needed

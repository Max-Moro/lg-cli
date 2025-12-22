## Архитектура Code Optimization (Public API + Function Bodies)

Этот документ описывает целевую архитектуру для подсистем оптимизации кода:
- **Public API optimization** — фильтрация приватных элементов
- **Function body optimization** — удаление/обрезка тел функций

---

### Цели архитектуры

1. **Унификация** — единая декларативная модель для обеих оптимизаций
2. **Консистентность с Literals** — аналогичный подход (дескриптор + профили + компоненты)
3. **Инкапсуляция языковой логики** — всё в пакетах языков, не в `optimizations/`
4. **Разделение ответственности** — анализ структуры отдельно от применения оптимизаций
5. **Минимизация дублирования** — единый источник истины для visibility/export логики

---

### Ключевые изменения относительно текущей архитектуры

| Аспект | Было | Станет |
|--------|------|--------|
| Центральный класс | `CodeAnalyzer` (ABC с 10+ abstract methods) | `LanguageCodeDescriptor` (декларативная конфигурация) |
| Языковая логика | `optimizations/public_api/language_profiles/<lang>.py` | `<lang>/code_profiles.py` |
| Function body queries | `<lang>/queries.py` (отдельно) | Объединены в профилях |
| Модель элемента | `ElementInfo` + `FunctionGroup` (перекрытие) | `CodeElement` (унифицированная) |
| Определение публичности | `visibility_check` + `export_check` + `uses_visibility_for_public_api` | Один `is_public` callback |

---

### Структура подсистемы

```
lg/adapters/
│
├── optimizations/
│   └── code/                           # Unified code optimization
│       ├── __init__.py
│       ├── descriptor.py               # LanguageCodeDescriptor
│       ├── profiles.py                 # ElementProfile
│       ├── models.py                   # CodeElement
│       ├── collector.py                # ElementCollector (универсальный)
│       ├── public_api_optimizer.py     # PublicApiOptimizer
│       └── function_body_optimizer.py  # FunctionBodyOptimizer
│
├── python/
│   ├── code_profiles.py               # PYTHON_CODE_DESCRIPTOR
│   └── ...
│
├── typescript/
│   ├── code_profiles.py               # TYPESCRIPT_CODE_DESCRIPTOR
│   └── ...
│
└── ... (другие языки)
```

---

### ER-модель

#### ElementProfile

Описывает тип элемента кода (класс, функция, метод, поле и т.д.):

```python
@dataclass
class ElementProfile:
    """Декларативное описание типа элемента кода."""

    name: str
    """Имя профиля для метрик и placeholders: "class", "method", "field"."""

    query: str
    """Tree-sitter query для поиска элементов. Capture: @element."""

    # --- Public API determination ---
    is_public: Optional[Callable[[Node, Doc], bool]] = None
    """
    Определяет, входит ли элемент в публичный API.
    None = всегда public (по умолчанию).

    Единый callback инкапсулирует всю логику:
    - Python: проверка _ и __ префиксов
    - Go: проверка регистра первой буквы
    - Java/Kotlin: проверка access modifiers
    - TypeScript top-level: проверка export keyword
    - TypeScript members: проверка private/protected
    """

    # --- Filtering ---
    additional_check: Optional[Callable[[Node, Doc], bool]] = None
    """Дополнительная фильтрация (например, is_case_class, is_inside_class)."""

    # --- Function body specific ---
    has_body: bool = False
    """True для элементов с телом (functions, methods)."""

    body_query: Optional[str] = None
    """Query для извлечения тела. Capture: @body. Если None — ищем child "block"."""

    docstring_extractor: Optional[Callable[[Node, Doc], Optional[Node]]] = None
    """Извлечение docstring для сохранения при strip."""

    # --- Inheritance ---
    parent_profile: Optional[str] = None
    """Имя родительского профиля для наследования."""
```

#### CodeElement

Унифицированная модель элемента кода (заменяет ElementInfo + FunctionGroup):

```python
@dataclass
class CodeElement:
    """Результат анализа элемента кода."""

    # Идентификация
    profile: ElementProfile
    node: Node
    name: Optional[str] = None

    # Public API status (вычисляется через profile.is_public)
    is_public: bool = True

    # Function body info (заполняется только если profile.has_body)
    body_node: Optional[Node] = None
    body_range: Optional[Tuple[int, int]] = None  # (start_byte, end_byte)
    docstring_node: Optional[Node] = None
    decorators: List[Node] = field(default_factory=list)
```

#### LanguageCodeDescriptor

Центральная декларация языка (аналог LanguageLiteralDescriptor):

```python
@dataclass
class LanguageCodeDescriptor:
    """Декларативное описание элементов кода для языка."""

    language: str
    """Имя языка: "python", "typescript", etc."""

    profiles: List[ElementProfile]
    """Все профили элементов для этого языка."""

    # --- Language-specific utilities ---
    decorator_types: Set[str] = field(default_factory=set)
    """Node types для декораторов: {"decorator", "annotation"}."""

    comment_types: Set[str] = field(default_factory=set)
    """Node types для комментариев: {"comment", "line_comment"}."""
```

---

### Компоненты

#### ElementCollector

Универсальный сборщик элементов по профилям:

```python
class ElementCollector:
    """Собирает CodeElement по профилям из дескриптора."""

    def __init__(self, doc: TreeSitterDocument, descriptor: LanguageCodeDescriptor):
        self.doc = doc
        self.descriptor = descriptor

    def collect_all(self) -> List[CodeElement]:
        """Собрать все элементы всех профилей."""
        pass

    def collect_by_profile(self, profile_name: str) -> List[CodeElement]:
        """Собрать элементы конкретного профиля."""
        pass

    def collect_private(self) -> List[CodeElement]:
        """Собрать только приватные элементы (для public API opt)."""
        pass

    def collect_with_bodies(self) -> List[CodeElement]:
        """Собрать только элементы с телами (для function body opt)."""
        pass
```

#### PublicApiOptimizer

Оптимизатор публичного API:

```python
class PublicApiOptimizer:
    """Удаляет приватные элементы из кода."""

    def __init__(self, adapter: CodeAdapter):
        self.adapter = adapter

    def apply(self, context: ProcessingContext) -> None:
        descriptor = self.adapter.get_code_descriptor()
        collector = ElementCollector(context.doc, descriptor)

        # Собираем элементы где is_public=False
        private_elements = collector.collect_private()
        private_elements = self._filter_nested(private_elements)

        for element in sorted(private_elements, key=lambda e: -e.node.start_byte):
            range_with_decorators = self._get_full_range(element)
            context.add_placeholder(
                element.profile.name,
                range_with_decorators[0],
                range_with_decorators[1]
            )
```

#### FunctionBodyOptimizer

Оптимизатор тел функций:

```python
class FunctionBodyOptimizer:
    """Удаляет/обрезает тела функций."""

    def __init__(self, adapter: CodeAdapter):
        self.adapter = adapter
        self.trimmer = FunctionBodyTrimmer(...)

    def apply(self, context: ProcessingContext, cfg: FunctionBodyConfig) -> None:
        descriptor = self.adapter.get_code_descriptor()
        collector = ElementCollector(context.doc, descriptor)

        elements_with_bodies = collector.collect_with_bodies()

        for element in elements_with_bodies:
            # Используем element.is_public для policy="keep_public"
            decision = self._evaluate_decision(element, cfg)

            if decision.action == "strip":
                self._apply_strip(context, element)
            elif decision.action == "trim":
                self._apply_trim(context, element)
```

---

### Языковые дескрипторы

Каждый язык определяет свой дескриптор в `<lang>/code_profiles.py`:

```python
# python/code_profiles.py

from lg.adapters.optimizations.code import (
    LanguageCodeDescriptor,
    ElementProfile,
)

def _is_public_python(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Python public API by naming convention.

    - __name__ (dunder) = public
    - __name (double underscore) = private
    - _name (single underscore) = private (protected)
    - name = public
    """
    name = _extract_name(node, doc)
    if not name:
        return True  # No name = public by default
    if name.startswith("__") and name.endswith("__"):
        return True  # dunder methods are public
    if name.startswith("_"):
        return False  # _ or __ prefix = private
    return True


def _find_python_docstring(node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """Find docstring at start of function body."""
    # ... implementation
    pass


PYTHON_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="python",

    profiles=[
        ElementProfile(
            name="class",
            query="(class_definition) @element",
            is_public=_is_public_python,
        ),

        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_python,
            additional_check=lambda n, d: not _is_inside_class(n),
            has_body=True,
            docstring_extractor=_find_python_docstring,
        ),

        ElementProfile(
            name="method",
            query="(function_definition) @element",
            is_public=_is_public_python,
            additional_check=lambda n, d: _is_inside_class(n),
            has_body=True,
            docstring_extractor=_find_python_docstring,
        ),

        ElementProfile(
            name="variable",
            query="(assignment) @element",
            is_public=_is_public_python,
            additional_check=lambda n, d: not _is_inside_class(n),
        ),
    ],

    decorator_types={"decorator"},
    comment_types={"comment"},
)
```

---

### Интеграция с адаптером

```python
# code_base.py

class CodeAdapter(BaseAdapter[C], ABC):

    @abstractmethod
    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return language code descriptor."""
        pass

    # Удаляем:
    # - create_code_analyzer()
    # - все зависимости от CodeAnalyzer


# python/adapter.py

class PythonAdapter(CodeAdapter[PythonCfg]):

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        from .code_profiles import PYTHON_CODE_DESCRIPTOR
        return PYTHON_CODE_DESCRIPTOR
```

---

### Миграция

#### Этап 1: Создание новой инфраструктуры
- Создать `lg/adapters/optimizations/code/` с новыми моделями
- Реализовать `ElementCollector`
- Написать тесты на новую инфраструктуру

#### Этап 2: Миграция профилей по языкам
- Для каждого языка создать `<lang>/code_profiles.py`
- Перенести логику из `language_profiles/<lang>.py`
- Перенести логику visibility из `<lang>/code_analysis.py`
- Удалить старые файлы

#### Этап 3: Миграция оптимизаторов
- Переписать `PublicApiOptimizer` на использование дескриптора
- Переписать `FunctionBodyOptimizer` на использование дескриптора
- Удалить зависимости от `CodeAnalyzer`

#### Этап 4: Очистка
- Удалить `lg/adapters/code_analysis.py`
- Удалить `lg/adapters/<lang>/code_analysis.py`
- Удалить `lg/adapters/optimizations/public_api/language_profiles/`
- Обновить документацию

---

### Ключевые принципы

1. **Декларативность** — профили описывают ЧТО искать и КАК определять публичность
2. **Единый источник истины** — один `is_public` callback вместо трёх полей
3. **Языковая инкапсуляция** — всё в пакетах языков (`<lang>/code_profiles.py`)
4. **Консистентность с Literals** — аналогичная структура дескриптор + профили
5. **Разделение сбора и применения** — Collector собирает, Optimizer применяет
6. **Унификация моделей** — один `CodeElement` вместо ElementInfo + FunctionGroup

---

### Сравнение с Literals architecture

| Аспект | Literals | Code (новая) |
|--------|----------|--------------|
| Дескриптор | `LanguageLiteralDescriptor` | `LanguageCodeDescriptor` |
| Профили | `StringProfile`, `SequenceProfile`, ... | `ElementProfile` |
| Сбор | Query в pipeline | `ElementCollector` |
| Обработка | `LiteralProcessor` компоненты | `PublicApiOptimizer`, `FunctionBodyOptimizer` |
| Языковая логика | `<lang>/literals.py` | `<lang>/code_profiles.py` |
| Публичность | N/A | `is_public` callback в профиле |

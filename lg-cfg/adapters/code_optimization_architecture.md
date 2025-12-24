## Архитектура Code Optimization

Этот документ описывает архитектуру подсистем оптимизации кода:
- **Public API optimization** — фильтрация приватных элементов
- **Function body optimization** — удаление/обрезка тел функций

---

### Цели архитектуры

1. **Унификация** — единая декларативная модель для обеих оптимизаций
2. **Инкапсуляция языковой логики** — всё в пакетах языков, не в `optimizations/`
3. **Разделение ответственности** — анализ структуры отдельно от применения оптимизаций
4. **Минимизация дублирования** — единый источник истины для visibility/export логики

---

### Структура подсистемы

```
lg/adapters/
│
├── optimizations/
│   ├── shared/                         # Общая инфраструктура для code-оптимизаций
│   │   ├── descriptor.py               # LanguageCodeDescriptor
│   │   ├── profiles.py                 # ElementProfile
│   │   ├── models.py                   # CodeElement
│   │   └── collector.py                # ElementCollector
│   │
│   ├── function_bodies/                # Оптимизация тел функций
│   │   ├── optimizer.py                # FunctionBodyOptimizer
│   │   ├── decision.py                 # FunctionBodyDecision
│   │   ├── evaluators.py               # Evaluators для политик
│   │   └── trimmer.py                  # FunctionBodyTrimmer
│   │
│   └── public_api/                     # Оптимизация публичного API
│       └── optimizer.py                # PublicApiOptimizer
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

### Модель данных

#### ElementProfile

Декларативное описание типа элемента кода (класс, функция, метод, поле и т.д.).

**Основные поля:**
- `name: str` — имя профиля для метрик и placeholders
- `query: str` — Tree-sitter query для поиска элементов
- `is_public: Callable[[Node, Doc], bool]` — единый callback для определения публичности
- `has_body: bool` — True для элементов с телами (functions, methods)
- `additional_check: Callable` — дополнительная фильтрация (is_inside_class и т.д.)
- `docstring_extractor: Callable` — извлечение docstring для сохранения
- `parent_profile: str` — имя родительского профиля для наследования

**Принцип работы `is_public`:**

Единый callback инкапсулирует всю логику определения публичности:
- Python: проверка префиксов `_` и `__`
- Go: проверка регистра первой буквы
- Java/Kotlin: проверка access modifiers
- TypeScript top-level: проверка export keyword
- TypeScript members: проверка private/protected

#### CodeElement

Унифицированная модель элемента кода.

**Основные поля:**
- `profile: ElementProfile` — профиль элемента
- `node: Node` — Tree-sitter узел
- `name: str` — имя элемента (для `except_patterns`)
- `is_public: bool` — результат вычисления через `profile.is_public`
- `body_node: Node` — узел тела (для функций/методов)
- `body_range: Tuple[int, int]` — диапазон для stripping
- `docstring_node: Node` — узел docstring (для сохранения)
- `decorators: List[Node]` — список декораторов

#### LanguageCodeDescriptor

Центральная декларация языка. Аналог `LanguageLiteralDescriptor` для кодовых элементов.

**Основные поля:**
- `language: str` — имя языка
- `profiles: List[ElementProfile]` — все профили элементов
- `decorator_types: Set[str]` — типы узлов для декораторов
- `comment_types: Set[str]` — типы узлов для комментариев
- `name_extractor: Callable` — извлечение имени элемента
- `extend_element_range: Callable` — расширение диапазона элемента

---

### Компоненты

#### ElementCollector

Универсальный сборщик элементов по профилям из дескриптора.

**Методы:**
- `collect_all()` — собрать все элементы всех профилей
- `collect_by_profile(name)` — собрать элементы конкретного профиля
- `collect_private()` — собрать только приватные элементы (для public API)
- `collect_with_bodies()` — собрать только элементы с телами (для function bodies)

**Принцип работы:**
1. Выполняет Tree-sitter queries из профилей
2. Применяет `additional_check` для фильтрации
3. Вычисляет `is_public` через callback профиля
4. Извлекает body_node, docstring, decorators
5. Создает `CodeElement` с полной информацией

#### ProcessingContext

Расширен для кэширования `ElementCollector`.

**Новый метод:**
- `get_collector()` — lazy-создание и кэширование collector

**Преимущества кэширования:**
- Tree-sitter queries выполняются один раз
- Оба оптимизатора видят консистентные данные
- Создаётся только если хотя бы один оптимизатор включен

#### PublicApiOptimizer

Удаляет приватные элементы из кода.

**Алгоритм:**
1. Получить `collector` из контекста
2. Собрать приватные элементы: `collector.collect_private()`
3. Отфильтровать вложенные элементы
4. Для каждого элемента создать placeholder

#### FunctionBodyOptimizer

Удаляет/обрезает тела функций.

**Алгоритм:**
1. Получить `collector` из контекста
2. Собрать элементы с телами: `collector.collect_with_bodies()`
3. Для каждого элемента:
   - Вычислить decision через evaluators
   - Применить strip или trim
   - Создать placeholder

**Evaluators:**
- `ExceptPatternEvaluator` — проверка `except_patterns`
- `KeepAnnotatedEvaluator` — проверка `keep_annotated`
- `BasePolicyEvaluator` — базовая политика (keep_all/strip_all/keep_public)

**Trimmer:**
- `FunctionBodyTrimmer` — обрезка тела до токенового бюджета
- Сохраняет prefix (начало тела)
- Сохраняет suffix (return statement)
- Вставляет placeholder между ними

---

### Языковые дескрипторы

Каждый язык определяет свой дескриптор в `<lang>/code_profiles.py`.

**Структура дескриптора:**
1. Helper-функции для определения публичности (`_is_public_<lang>`)
2. Helper-функции для извлечения элементов (`_extract_name`, `_find_docstring`)
3. Константа `<LANG>_CODE_DESCRIPTOR` с профилями

**Примеры профилей:**

Python:
- `class`, `function`, `method`, `variable`
- Публичность по naming convention (_name, __name)

TypeScript:
- `class`, `interface`, `type`, `enum`, `namespace`
- `function` (top-level и namespace), `method`, `field`, `variable`
- `import` (для фильтрации re-exports)
- Top-level: публичность по export keyword
- Members: публичность по visibility modifiers

Java:
- `class`, `interface`, `enum`, `annotation`
- `function`, `method`, `field`, `variable`
- Публичность по access modifiers

---

### Интеграция с адаптером

**CodeAdapter:**
- Абстрактный метод: `get_code_descriptor() -> LanguageCodeDescriptor`
- Используется в `_post_bind()` для создания оптимизаторов

**Пример в языковом адаптере:**
```python
def get_code_descriptor(self) -> LanguageCodeDescriptor:
    from .code_profiles import PYTHON_CODE_DESCRIPTOR
    return PYTHON_CODE_DESCRIPTOR
```

---

### Ключевые принципы

1. **Декларативность** — профили описывают ЧТО искать и КАК определять публичность
2. **Единый источник истины** — один `is_public` callback вместо множества полей
3. **Языковая инкапсуляция** — всё в пакетах языков (`<lang>/code_profiles.py`)
4. **Разделение сбора и применения** — Collector собирает, Optimizer применяет
5. **Унификация моделей** — один `CodeElement` для всех оптимизаций
6. **Кэширование Collector** — переиспользование между оптимизаторами

# Архитектура Literals Optimization

Подсистема оптимизации литералов для языковых адаптеров является наиболее сложной и развитой. Это обусловлено тем, что реальные языки программирования достаточно сильно отличаются правилами и синтаксисом декларации различных литералов. Данная система позволяет настраивать паттерны литералов в декларативном формате, вместо подхода через индивидуальные императивные хуки в каждом конечном языковом адаптере. Но из-за этого ей приходится учитывать множество особенностей и нюансов адаптации под конкретные потребности языков.

---

## Основная структура подсистемы оптимизации литералов

```
lg/adapters/optimizations/literals/
├── processing/                 # Универсальные стадии пайплайна
│   ├── __init__.py
│   ├── pipeline.py             # LiteralPipeline (оркестратор)
│   ├── parser.py               # LiteralParser (парсинг структуры)
│   ├── selector.py             # BudgetSelector (выбор элементов)
│   └── formatter.py            # ResultFormatter (форматирование)
│
├── components/                 # Опциональные специализированные компоненты
│   ├── __init__.py
│   ├── ast_sequence.py         # AST-based последовательности (C/C++ concatenated strings)
│   └── block_init.py           # Imperative initialization (Java double-brace, Rust HashMap)
│
├── utils/                      # Утилитарные модули
│   ├── __init__.py
│   ├── element_parser.py       # Парсинг содержимого элементов
│   ├── interpolation.py        # Обработка интерполяции в строках
│   └── indentation.py          # Определение отступов
│
├── __init__.py                 # Публичный API
├── descriptor.py               # Декларативная модель языковых паттернов
└── patterns.py                 # Иерархия профилей литералов
```

---

## Принципы архитектуры

### 1. Четкое разделение на три типа модулей

#### Универсальные стадии пайплайна (`processing/`)

**Характеристики**:
- Выполняются последовательно друг за другом
- Существуют в пайплайне всегда
- Работают с любыми языками и любыми видами литералов
- Обмениваются данными через явную ER-модель

**Стадии**:
- `pipeline.py` — оркестрация всего процесса
- `parser.py` — парсинг структуры литерала → `ParsedLiteral`
- `selector.py` — выбор элементов по бюджету → `Selection`/`DFSSelection`
- `formatter.py` — форматирование результата → `TrimResult`

#### Опциональные специализированные компоненты (`components/`)

**Характеристики**:
- Обрабатывают особые виды литералов или особые случаи
- Нужны только для определенных языков или паттернов
- Подключаются по условию или флагу в декларативной конфигурации
- Автономны: сами решают применимость через `can_handle()`

**Компоненты**:
- `ast_sequence.py` — обработка последовательностей без явных разделителей
- `block_init.py` — обработка imperative initialization блоков

#### Утилитарные модули (`utils/`)

**Характеристики**:
- Используются повсеместно разными стадиями и компонентами
- Не содержат бизнес-логики оптимизации
- Предоставляют вспомогательные функции

**Утилиты**:
- `element_parser.py` — парсинг элементов внутри литералов
- `interpolation.py` — работа с интерполяцией в строках
- `indentation.py` — определение отступов в исходном коде

### 2. Оркестратор как координатор

`processing/pipeline.py` — **единственный оркестратор** всего процесса:

**Задачи оркестратора**:
- Управление двухпроходной логикой (strings → collections)
- Координация вызовов стадий и компонентов
- Создание и конфигурирование зависимостей
- Фильтрация top-level vs nested узлов

**Чего НЕ делает оркестратор**:
- ❌ Не содержит детальной логики парсинга/форматирования
- ❌ Не проверяет условия применимости компонентов
- ❌ Не подготавливает параметры для компонентов
- ❌ Не маршрутизирует на разные пути обработки

**Объем**: ~200-300 строк чистой координации

### 3. Автономность компонентов

Каждый специализированный компонент полностью автономен:

```python
class SpecializedComponent:
    def can_handle(self, profile, node, doc) -> bool:
        """Компонент сам решает, применим ли он."""
        ...

    def process(self, node, doc, source_text, profile, budget) -> Optional[TrimResult]:
        """
        Полная автономная обработка.

        Компонент сам:
        - Извлекает нужные данные
        - Определяет параметры
        - Парсит структуру
        - Форматирует результат
        """
        ...
```

**Преимущества**:
- Pipeline не знает о внутренностях компонента
- Легко добавлять новые компоненты
- Тестирование компонентов изолированно

### 4. Расширенные стадии

Стадии предоставляют богатый API для работы на разных уровнях:

```python
# LiteralParser - низкий и высокий уровень
class LiteralParser:
    def parse_from_node(self, node, doc, source_text, profile):
        """Высокоуровневый API: автоматически всё определяет."""
        ...

    def parse_literal_with_profile(self, text, profile, ...):
        """Низкоуровневый API: требует готовых параметров."""
        ...

    @staticmethod
    def detect_base_indent(text, byte_pos):
        """Утилита: определение отступов."""
        ...
```

**Pipeline использует высокоуровневый API**, компоненты могут использовать любой уровень.

---

## Поток данных

### Стандартный путь (без специальных компонентов)

```
Node (Tree-sitter)
    ↓
[Parser] → ParsedLiteral (текст, структура, отступы, токены)
    ↓
[Selector] → Selection/DFSSelection (kept_elements, removed_elements)
    ↓
[Formatter] → TrimResult (trimmed_text, saved_tokens, comment)
    ↓
Context (применение к исходному коду)
```

### Путь через специальный компонент

```
Node (Tree-sitter)
    ↓
[Component.can_handle()] → true
    ↓
[Component.process()] → TrimResult
    ↓
Context (применение к исходному коду)
```

### Двухпроходная архитектура

**Pass 1: Строки** (top-level только)
- Обрабатываются все строковые литералы
- Применяется inline truncation с интерполяцией

**Pass 2: Коллекции** (DFS с рекурсией)
- Обрабатываются все коллекции (sequences, mappings, factories, blocks)
- Применяется DFS для вложенных структур

**Зачем два прохода**:
- Ортогональность: строки и коллекции — разные стратегии
- Упрощение: не нужно решать коллизии inline vs DFS
- Эффективность: каждый проход оптимизирован под свой тип

---

## ER-модель между стадиями

### ParsedLiteral
```python
@dataclass
class ParsedLiteral(Generic[P]):
    """Результат парсинга."""
    original_text: str
    start_byte: int
    end_byte: int
    profile: P                    # StringProfile | CollectionProfile
    opening: str
    closing: str
    content: str
    is_multiline: bool
    base_indent: str
    element_indent: str
    wrapper: Optional[str]
    original_tokens: int
```

### Selection / DFSSelection
```python
@dataclass
class Selection:
    """Результат выбора элементов (flat)."""
    kept_elements: List[Element]
    removed_elements: List[Element]
    total_count: int
    tokens_kept: int
    tokens_removed: int

@dataclass
class DFSSelection(Selection):
    """Результат выбора с рекурсией."""
    nested_selections: Dict[int, DFSSelection]
    remaining_budget: int
    budget_exhausted: bool
```

### TrimResult
```python
@dataclass
class TrimResult:
    """Финальный результат оптимизации."""
    trimmed_text: str
    original_tokens: int
    trimmed_tokens: int
    saved_tokens: int
    elements_kept: int
    elements_removed: int
    comment_text: Optional[str]
    comment_position: Optional[int]
```

---

## Расширяемость

### Добавление нового языка

1. Создать дескриптор в `lg/adapters/<язык>/literals.py`
2. Определить профили (StringProfile, SequenceProfile, ...)
3. Если нужен специальный компонент — создать в `components/`

**Пример нового компонента**:
```python
# components/my_special.py
class MySpecialProcessor:
    def can_handle(self, profile, node, doc) -> bool:
        return profile.some_flag  # Проверка применимости

    def process(self, node, doc, source_text, profile, budget):
        # Полная автономная обработка
        ...
        return TrimResult(...)
```

**Регистрация**:
```python
# processing/pipeline.py
def __init__(self, cfg, adapter):
    self.special_components = [
        ASTSequenceProcessor(...),
        BlockInitProcessor(...),
        MySpecialProcessor(...),  # Добавить сюда
    ]
```

### Добавление нового типа профиля

1. Создать класс в `patterns.py` (наследник `LiteralProfile`)
2. Реализовать обработку в стадиях или компоненте
3. Добавить в дескриптор языка

---

## Граница ответственности Pipeline vs Компоненты

### Pipeline отвечает за:
- ✅ Координацию проходов (Pass 1, Pass 2)
- ✅ Фильтрацию top-level vs nested узлов
- ✅ Цикл по компонентам с проверкой `can_handle()`
- ✅ Вызов стадий для стандартного пути
- ✅ Применение результатов к context

### Компоненты отвечают за:
- ✅ Проверку применимости (`can_handle`)
- ✅ Извлечение данных из Tree-sitter
- ✅ Определение параметров (отступы, структура)
- ✅ Парсинг/форматирование специальных случаев
- ✅ Возврат готового `TrimResult`

**Правило**: Если логика протекла из компонента в pipeline — граница выбрана неверно, нужно больше переносить в компонент.

---

## Корневой пакет

Корневой пакет `literals/` содержит:

- **Публичный API** (`__init__.py`) — экспорт основных классов
- **Декларативная модель** (`descriptor.py`) — `LanguageLiteralDescriptor`
- **Профили паттернов** (`patterns.py`) — иерархия `LiteralProfile`

**Не содержит**:
- ❌ Императивной логики обработки
- ❌ Утилитарных функций (они в `utils/`)
- ❌ Компонентов или стадий

---

## Итоги

**Ключевые принципы**:

1. **Единый оркестратор** — `pipeline.py` координирует всё
2. **Автономные компоненты** — сами решают применимость и делают всё внутри
3. **Богатые стадии** — предоставляют API на разных уровнях
4. **Явная ER-модель** — стадии обмениваются через типизированные структуры
5. **Четкая классификация** — processing / components / utils

**Результат**: Чистая, расширяемая архитектура с минимальной связностью модулей.

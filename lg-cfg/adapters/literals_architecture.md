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
│   ├── string_formatter.py     # StringFormatter (форматирование строк)
│   └── collection_formatter.py # CollectionFormatter (форматирование коллекций с DFS)
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
│   ├── indentation.py          # Определение отступов
│   └── comment_formatter.py    # CommentFormatter (утилиты комментирования)
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
- `string_formatter.py` — форматирование строк → `FormattedResult`
- `collection_formatter.py` — форматирование коллекций с DFS → `FormattedResult`

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
- `comment_formatter.py` — генерация и форматирование комментариев (shared для обоих форматтеров)

### 2. Оркестратор как координатор

`processing/pipeline.py` — **единственный оркестратор** всего процесса:

**Задачи оркестратора**:
- Управление единой логикой обработки всех типов литералов
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

### 5. Специализация форматтеров

Форматирование разделено на два специализированных модуля вместо одного монолитного:

**StringFormatter** (`string_formatter.py`, ~89 строк):
- Обрабатывает **только** строковые литералы
- Простое усечение с добавлением многоточия `…`
- Явная типизация: `ParsedLiteral[StringProfile]` + `Selection`
- Никакой DFS, рекурсии, вложенных структур
- Никаких проверок `isinstance()`

**CollectionFormatter** (`collection_formatter.py`, ~342 строки):
- Обрабатывает **только** коллекции
- Полная поддержка DFS с рекурсивной обработкой вложенности
- Явная типизация: `ParsedLiteral[CollectionProfile]` + `DFSSelection`
- Multiline/single-line форматирование
- Группировка tuple для Map.of паттернов
- Inline threshold для вложенных структур

**CommentFormatter** (`utils/comment_formatter.py`, ~140 строк):
- Универсальные утилиты комментирования
- Shared компонент для обоих форматтеров
- Генерация текста с информацией об экономии токенов
- Контекстное форматирование (single-line vs block)
- Определение точек вставки

**Преимущества специализации**:
- ✅ Явная типизация без проверок типов
- ✅ Упрощение логики каждого форматтера
- ✅ Изолированное тестирование
- ✅ Независимое развитие функциональности

---

## Поток данных

### Стандартный путь (без специальных компонентов)

**Для строк:**
```
Node (Tree-sitter)
    ↓
[Parser] → ParsedLiteral[StringProfile]
    ↓
[Selector] → Selection (kept_elements, removed_elements)
    ↓
[StringFormatter] → FormattedResult (truncated string with …)
    ↓
Context (применение к исходному коду)
```

**Для коллекций:**
```
Node (Tree-sitter)
    ↓
[Parser] → ParsedLiteral[CollectionProfile]
    ↓
[Selector] → DFSSelection (with nested_selections)
    ↓
[CollectionFormatter] → FormattedResult (formatted collection with DFS)
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

### Единопроходная архитектура

**Единый проход** обрабатывает все типы литералов:
- Строки (StringProfile) — inline truncation с интерполяцией
- Коллекции (SequenceProfile, MappingProfile) — DFS с рекурсией
- Фабрики (FactoryProfile) — DFS с поддержкой tuple_size
- Блоки инициализации (BlockInitProfile) — специализированная обработка

**Преимущества единого прохода**:
- Упрощение логики оркестратора
- Единообразная обработка всех типов профилей
- Меньше дублирования кода
- Более гибкое добавление новых типов литералов

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

### FormattedResult
```python
@dataclass
class FormattedResult:
    """Результат форматирования (из StringFormatter / CollectionFormatter)."""
    text: str                      # Отформатированный текст
    start_byte: int               # Диапазон замены
    end_byte: int
    comment: Optional[str]        # Внешний комментарий (если нужен)
    comment_byte: Optional[int]   # Позиция вставки комментария
```

### TrimResult
```python
@dataclass
class TrimResult:
    """Результат компонента (ASTSequenceProcessor, BlockInitProcessor)."""
    trimmed_text: str
    original_tokens: int
    trimmed_tokens: int
    saved_tokens: int
    elements_kept: int
    elements_removed: int
    comment_text: Optional[str]
    comment_position: Optional[int]
    nodes_to_replace: Optional[list]  # Для групповой замены (BLOCK_INIT)
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
- ✅ Координацию единого прохода со всеми типами профилей
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
2. **Единопроходная обработка** — все типы литералов обрабатываются в одном проходе
3. **Автономные компоненты** — сами решают применимость и делают всё внутри
4. **Богатые стадии** — предоставляют API на разных уровнях
5. **Явная ER-модель** — стадии обмениваются через типизированные структуры
6. **Четкая классификация** — processing / components / utils
7. **Унифицированный дескриптор** — все профили в одном списке
8. **Специализация форматтеров** — отдельные модули для строк и коллекций без проверок типов

**Результат**: Чистая, расширяемая архитектура с минимальной связностью модулей, явной типизацией и упрощенной логикой координации.

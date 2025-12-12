# Архитектура Literals Optimization

Подсистема оптимизации литералов для языковых адаптеров является наиболее сложной и развитой. Это обусловлено тем, что реальные языки программирования достаточно сильно отличаются правилами и синтаксисом декларации различных литералов. Данная система позволяет настраивать паттерны литералов в декларативном формате, вместо подхода через индивидуальные императивные хуки в каждом конечном языковом адаптере. Но из-за этого ей приходится учитывать множество особенностей и нюансов адаптации под конкретные потребности языков.

---

## Основная структура подсистемы оптимизации литералов

```
lg/adapters/optimizations/literals/
├── processing/                 # Универсальные стадии и сервисы
│   ├── __init__.py
│   ├── pipeline.py             # LiteralPipeline (оркестратор, ~276 строк)
│   ├── parser.py               # LiteralParser (парсинг структуры)
│   ├── selector.py             # BudgetSelector (выбор элементов)
│   ├── string_formatter.py     # StringFormatter (форматирование строк)
│   └── collection_formatter.py # CollectionFormatter (форматирование коллекций с DFS)
│
├── components/                 # Автономные компоненты обработки
│   ├── __init__.py
│   ├── string_literal.py       # StringLiteralProcessor (строковые литералы)
│   ├── standard_collections.py # StandardCollectionsProcessor (стандартные коллекции)
│   ├── ast_sequence.py         # ASTSequenceProcessor (AST-based последовательности)
│   └── block_init.py           # BlockInitProcessor (imperative initialization)
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

#### Универсальные стадии и сервисы (`processing/`)

**Характеристики**:
- Предоставляют shared сервисы для всех компонентов
- Создаются один раз в pipeline
- Работают с любыми языками и любыми видами литералов
- Обмениваются данными через явную ER-модель

**Стадии и сервисы**:
- `pipeline.py` — оркестрация всего процесса (~276 строк)
- `parser.py` — shared LiteralParser для всех компонентов
- `selector.py` — shared BudgetSelector для выбора элементов
- `string_formatter.py` — специализированное форматирование строк
- `collection_formatter.py` — специализированное форматирование коллекций с DFS

#### Автономные компоненты обработки (`components/`)

**Характеристики**:
- Полностью автономные процессоры для конкретных типов литералов
- Инкапсулируют всю логику от парсинга до форматирования
- Используют shared сервисы из pipeline
- Сами решают применимость через `can_handle()`
- Регистрируются в pipeline в priority order

**Компоненты**:
- `string_literal.py` — **StringLiteralProcessor** (строковые литералы)
  - Обрабатывает все StringProfile
  - Использует LiteralParser, StringFormatter
  - Поддерживает интерполяцию

- `standard_collections.py` — **StandardCollectionsProcessor** (стандартные коллекции)
  - Обрабатывает SequenceProfile, MappingProfile, FactoryProfile
  - Использует LiteralParser, CollectionFormatter, BudgetSelector
  - Инкапсулирует кэш ElementParser'ов
  - Поддерживает DFS для вложенных структур

- `ast_sequence.py` — **ASTSequenceProcessor** (AST-based последовательности)
  - Обрабатывает SequenceProfile с requires_ast_extraction=True
  - Специальный случай для C/C++ concatenated strings

- `block_init.py` — **BlockInitProcessor** (imperative initialization)
  - Обрабатывает BlockInitProfile
  - Java double-brace initialization, Rust HashMap blocks

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

### 2. Pipeline как чистый координатор

`processing/pipeline.py` — **минималистичный оркестратор** (~276 строк):

**Что делает pipeline**:
- ✅ Создает shared сервисы (LiteralParser, BudgetSelector, CommentFormatter) — 1 раз
- ✅ Регистрирует компоненты в priority order
- ✅ Фильтрует top-level vs nested узлы
- ✅ Вызывает компоненты через `can_handle()` + `process()`
- ✅ Применяет результаты к context

**Чего НЕ делает pipeline**:
- ❌ Не содержит детальной логики парсинга/форматирования
- ❌ Не проверяет условия применимости компонентов (делегирует `can_handle`)
- ❌ Не подготавливает параметры для компонентов (использует shared сервисы)
- ❌ Не маршрутизирует на разные пути обработки (компоненты автономны)
- ❌ Не кэширует ElementParser'ы (инкапсулировано в StandardCollectionsProcessor)

**Shared сервисы** (создаются 1 раз, передаются в компоненты):
```python
self.selector = BudgetSelector(self.adapter.tokenizer)
self.comment_formatter = CommentFormatter(comment_style)
self.literal_parser = LiteralParser(self.adapter.tokenizer)
```

**Архитектура компонентов**:
```python
self.special_components = [
    # Специальные случаи (priority first)
    ASTSequenceProcessor(tokenizer, string_profiles),
    BlockInitProcessor(tokenizer, all_profiles, callback, comment_style),

    # Стандартные случаи
    StringLiteralProcessor(tokenizer, literal_parser, comment_formatter),
    StandardCollectionsProcessor(tokenizer, literal_parser, selector, comment_formatter, descriptor),
]
```

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

### Компонентная архитектура обработки

**Pipeline координирует компоненты**:
```
Node (Tree-sitter)
    ↓
Pipeline: цикл по компонентам
    ↓
Component.can_handle(profile, node, doc) → true/false
    ↓
Component.process(node, doc, source_text, profile, budget) → TrimResult
    ↓
Context (применение результата)
```

### StringLiteralProcessor (строки)

```
Node (Tree-sitter) + StringProfile
    ↓
[LiteralParser.parse_from_node()] → ParsedLiteral[StringProfile]
    ↓
[Tokenizer.truncate_to_tokens()] → truncated content
    ↓
[InterpolationHandler.adjust_truncation()] → adjusted content
    ↓
[StringFormatter.format()] → FormattedResult
    ↓
Return TrimResult
```

### StandardCollectionsProcessor (коллекции)

```
Node (Tree-sitter) + CollectionProfile
    ↓
[LiteralParser.parse_from_node()] → ParsedLiteral[CollectionProfile]
    ↓
[ElementParser.parse()] → List[Element]
    ↓
[BudgetSelector.select_dfs()] → DFSSelection (with nested)
    ↓
[CollectionFormatter.format_dfs()] → FormattedResult
    ↓
Return TrimResult
```

**Инкапсуляция**: StandardCollectionsProcessor внутренне управляет кэшем ElementParser'ов.

### Специальные компоненты

**ASTSequenceProcessor** (C/C++ concatenated strings):
```
Node + SequenceProfile[requires_ast_extraction=True]
    ↓
Извлечь child string nodes через Tree-sitter queries
    ↓
Выбрать строки по бюджету
    ↓
Вставить placeholder в последнюю строку
    ↓
Return TrimResult
```

**BlockInitProcessor** (Java double-brace, Rust HashMap):
```
Node + BlockInitProfile
    ↓
Извлечь initialization statements
    ↓
Выбрать statements по бюджету (с DFS для вложенных литералов)
    ↓
Форматировать с placeholder
    ↓
Return TrimResult (nodes_to_replace для групповой замены)
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
- ✅ Создание shared сервисов (1 раз при инициализации)
- ✅ Координацию единого прохода со всеми типами профилей
- ✅ Фильтрацию top-level vs nested узлов
- ✅ Цикл по компонентам с проверкой `can_handle()`
- ✅ Применение результатов к context (editor, metrics)

### Компоненты отвечают за:
- ✅ Проверку применимости через `can_handle(profile, node, doc)`
- ✅ Извлечение данных из Tree-sitter (через shared LiteralParser)
- ✅ Определение параметров (отступы, структура)
- ✅ Парсинг элементов (StandardCollectionsProcessor инкапсулирует ElementParser)
- ✅ Выбор элементов по бюджету (через shared BudgetSelector)
- ✅ Форматирование результата (через shared форматтеры)
- ✅ Возврат готового `TrimResult`

### Shared сервисы отвечают за:
- ✅ **LiteralParser**: парсинг структуры литералов (используется всеми компонентами)
- ✅ **BudgetSelector**: выбор элементов по бюджету (используется StandardCollectionsProcessor)
- ✅ **CommentFormatter**: форматирование комментариев (используется форматтерами)
- ✅ **StringFormatter**: форматирование строк (используется StringLiteralProcessor)
- ✅ **CollectionFormatter**: форматирование коллекций (используется StandardCollectionsProcessor)

**Инкапсуляция**: StandardCollectionsProcessor владеет кэшем ElementParser'ов — это его внутренняя деталь реализации.

**Правило**: Если логика протекла из компонента в pipeline — граница выбрана неверно, нужно больше переносить в компонент.

---

## Корневой пакет

Корневой пакет `literals/` содержит:

- **Публичный API** (`__init__.py`) — экспорт основных классов
- **Декларативная модель** (`descriptor.py`) — `LanguageLiteralDescriptor`
- **Профили паттернов** (`patterns.py`) — иерархия `LiteralProfile`

---

## Итоги

**Ключевые принципы**:

1. **Минималистичный оркестратор** — `pipeline.py` (~276 строк) только координирует
2. **Shared сервисы** — создаются 1 раз, передаются в компоненты
3. **Полностью автономные компоненты** — от `can_handle()` до `TrimResult`
4. **Компонентная архитектура** — 4 автономных процессора:
   - StringLiteralProcessor (строки)
   - StandardCollectionsProcessor (коллекции с инкапсулированным кэшем)
   - ASTSequenceProcessor (специальные последовательности)
   - BlockInitProcessor (imperative initialization)
5. **Инкапсуляция** — каждый компонент владеет своими данными
6. **Единопроходная обработка** — все типы литералов в одном проходе
7. **Явная ER-модель** — типизированные структуры данных
8. **Четкая классификация** — processing (сервисы) / components (процессоры) / utils (утилиты)
9. **Унифицированный дескриптор** — все профили в одном списке
10. **Специализация форматтеров** — отдельные модули для строк и коллекций


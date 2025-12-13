# Архитектура Literals Optimization

Подсистема оптимизации литералов — наиболее сложная часть языковых адаптеров. Она использует декларативный подход для настройки паттернов литералов вместо императивных хуков в каждом языковом адаптере, что требует учета множества языковых особенностей.

---

## Структура подсистемы

```
lg/adapters/optimizations/literals/
├── processing/                 # Shared сервисы
│   ├── pipeline.py             # LiteralPipeline (координатор)
│   ├── parser.py               # LiteralParser
│   ├── selector.py             # BudgetSelector
│   ├── string_formatter.py     # StringFormatter
│   └── collection_formatter.py # CollectionFormatter
│
├── components/                 # Автономные процессоры
│   ├── base.py                 # LiteralProcessor (интерфейс)
│   ├── string_literal.py       # StringLiteralProcessor
│   ├── standard_collections.py # StandardCollectionsProcessor
│   ├── ast_sequence.py         # ASTSequenceProcessor
│   ├── block_init.py           # BlockInitProcessorBase
│   ├── java_double_brace.py    # JavaDoubleBraceProcessor
│   └── rust_let_group.py       # RustLetGroupProcessor
│
├── utils/                      # Утилиты
│   ├── element_parser.py
│   ├── interpolation.py
│   ├── indentation.py
│   └── comment_formatter.py
│
├── descriptor.py               # LanguageLiteralDescriptor
└── patterns.py                 # Иерархия профилей
```

---

## Архитектурные принципы

### 1. Трехуровневая структура

**Processing (shared сервисы)**:
- Создаются 1 раз в pipeline
- Используются всеми компонентами
- Языконезависимые
- Обмен через типизированную ER-модель

**Components (автономные процессоры)**:
- Полная инкапсуляция логики для типа литерала
- Решение применимости через `can_handle()`
- Priority order регистрация
- Иерархия наследования от `LiteralProcessor`

**Utils (вспомогательные модули)**:
- Без бизнес-логики оптимизации
- Используются повсеместно

### 2. Компонентная архитектура

Все компоненты наследуют единый интерфейс `LiteralProcessor`:
- `can_handle(profile, node, doc) -> bool` — проверка применимости
- `process(...) -> Optional[TrimResult]` — полная обработка

**6 процессоров**:
- **StringLiteralProcessor** — строки с интерполяцией
- **StandardCollectionsProcessor** — коллекции с DFS (инкапсулирует кэш ElementParser)
- **ASTSequenceProcessor** — C/C++ concatenated strings
- **BlockInitProcessorBase** — базовый для императивной инициализации
  - **JavaDoubleBraceProcessor** — `new HashMap() {{ put(...); }}`
  - **RustLetGroupProcessor** — `let mut m = HashMap::new(); m.insert(...);`

### 3. Pipeline как минималистичный координатор

**Делает**:
- Создает shared сервисы (1 раз)
- Фильтрует top-level vs nested узлы
- Вызывает компоненты через `can_handle()` + `process()`
- Применяет результаты к context

**НЕ делает**:
- Парсинг/форматирование (делегирует компонентам)
- Проверку условий применимости (делегирует `can_handle`)
- Кэширование ElementParser (инкапсулировано в компоненте)

### 4. Специализация форматтеров

**StringFormatter** — только строки, simple truncation

**CollectionFormatter** — только коллекции, greedy selection, multiline/single-line

**CommentFormatter** — shared утилита для обоих форматтеров

### 5. Inside-Out Processing

**Принцип**: Все узлы от всех профилей сортируются вместе по глубине (deepest-first), затем обрабатываются в едином проходе.

**Композиция**: Глубокие узлы создают edits первыми, родительские узлы автоматически композируют их через `add_replacement_composing_nested`.

**Преимущество**: Depth важнее порядка профилей в дескрипторе - вложенные литералы разных типов обрабатываются корректно.

---

## Поток данных

**Общий**:
```
Node → Pipeline цикл → Component.can_handle() → Component.process() → TrimResult → Context
```

**StringLiteralProcessor**:
```
Node + StringProfile
  → LiteralParser.parse_from_node() → ParsedLiteral
  → Tokenizer.truncate_to_tokens() → truncated
  → InterpolationHandler.adjust_truncation() → adjusted
  → StringFormatter.format() → FormattedResult
  → TrimResult
```

**StandardCollectionsProcessor**:
```
Node + CollectionProfile
  → LiteralParser.parse_from_node() → ParsedLiteral
  → ElementParser.parse() → List[Element]
  → BudgetSelector.select() → Selection (greedy)
  → CollectionFormatter.format() → FormattedResult
  → TrimResult
```

**Inside-Out архитектура**: все типы литералов (строки, коллекции, фабрики, блоки) обрабатываются в едином проходе, отсортированном по глубине (deepest-first).

---

## ER-модель

**ParsedLiteral** — результат парсинга (original_text, opening, closing, content, is_multiline, base_indent, wrapper, profile)

**Selection** — выбор элементов (kept_elements, removed_elements, tokens_kept/removed)

**FormattedResult** — отформатированный текст (text, start/end_byte, comment, comment_byte)

**TrimResult** — финальный результат компонента (trimmed_text, tokens, elements, nodes_to_replace)

---

## Граница ответственности

**Pipeline**:
- Создание shared сервисов (1 раз)
- Координация единого прохода
- Фильтрация top-level/nested
- Цикл по компонентам
- Применение результатов

**Компоненты**:
- Проверка применимости
- Извлечение данных (через shared LiteralParser)
- Парсинг элементов
- Выбор по бюджету (через shared BudgetSelector)
- Форматирование (через shared форматтеры)
- Возврат TrimResult

**Shared сервисы**:
- **LiteralParser** — парсинг структуры
- **BudgetSelector** — выбор элементов
- **CommentFormatter** — комментирование
- **StringFormatter/CollectionFormatter** — специализированное форматирование

---

## Расширяемость

**Новый язык**:
1. Создать дескриптор `lg/adapters/<язык>/literals.py`
2. Определить профили (StringProfile, SequenceProfile, MappingProfile, FactoryProfile)
3. При необходимости создать специальный компонент в `components/`

**Новый компонент**:
- Наследовать `LiteralProcessor`
- Реализовать `can_handle()` и `process()`
- Зарегистрировать в pipeline в priority order

**Новый тип профиля**:
1. Создать класс в `patterns.py` (наследник `LiteralProfile`)
2. Реализовать обработку в компоненте
3. Добавить в дескриптор языка

---

## Ключевые принципы

1. **Единый интерфейс** — все компоненты наследуют `LiteralProcessor`
2. **Shared сервисы** — создаются 1 раз, передаются компонентам
3. **Автономность** — компоненты полностью самодостаточны
4. **Инкапсуляция** — каждый компонент владеет своими данными (кэш ElementParser в StandardCollectionsProcessor)
5. **Единопроходность** — все типы литералов в одном проходе
6. **Типизация** — явная ER-модель, `List[LiteralProcessor]` для static анализа
7. **Специализация** — отдельные форматтеры для строк и коллекций
8. **DFS оптимизация** — рекурсивная обработка вложенных структур

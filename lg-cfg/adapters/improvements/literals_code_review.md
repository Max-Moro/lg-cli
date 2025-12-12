## Code Review: Literals Optimization Subsystem

**Дата**: 2025-12-12
**Scope**: `lg/adapters/optimizations/literals/*`
**Поддерживаемые языки**: Python, TypeScript, Kotlin, C++, C, Java, JavaScript, Scala, Go, Rust

---

### Executive Summary

Подсистема оптимизации литералов является наиболее сложной частью языковых адаптеров. После добавления поддержки 10 языков проведен анализ архитектуры и выявлены следующие основные находки:

**Сильные стороны**:
- ✅ Четкое разделение на универсальные стадии, специализированные компоненты и утилиты
- ✅ Декларативная модель через профили вместо императивных хуков
- ✅ Единопроходная архитектура для всех типов литералов
- ✅ Автономность компонентов с явным `can_handle()`
- ✅ Богатый типизированный API между стадиями

**Проблемные области**:
- ⚠️ Дублирование логики между стадиями и компонентами
- ⚠️ Смешение ответственности в некоторых классах
- ⚠️ Недостаточная факторизация общего кода
- ⚠️ Неявные зависимости между модулями

---

### 1. Архитектурный анализ

#### 1.1. Разделение на модули

**Текущая структура соответствует заявленным принципам**:

```
processing/      — универсальные стадии (✅ соответствует)
components/      — специализированные компоненты (✅ соответствует)
utils/           — утилиты (✅ соответствует)
```

**Оценка**: 9/10

**Замечание**: Все модули находятся на правильных местах, граница ответственности в целом соблюдена.

---

#### 1.2. Оркестратор (`processing/pipeline.py`)

**Анализ объема**:
- Текущий размер: ~180 строк (без комментариев)
- Заявленный целевой размер: 200-300 строк
- **Оценка**: ✅ В норме

**Анализ функций**:

```python
class LiteralPipeline:
    def __init__(self, cfg, adapter)           # Инициализация зависимостей
    def apply(self, context)                    # Точка входа
    def _process_profile(self, context, ...)   # Обработка одного профиля
    def _process_literal(self, node, ...)      # Единая точка обработки
    def _apply_result(self, context, ...)      # Применение результата
    def _get_parser_for_profile(self, ...)    # Фабрика парсеров
```

**Проблемы**:

1. **Избыточная логика в `_process_literal`** (строки 138-228):
   - Условная логика для строк vs коллекций
   - Создание псевдо-Selection для строк
   - Вычисление overhead
   - Обработка интерполяции

   **Вердикт**: Часть этой логики должна быть в стадиях, а не в оркестраторе.

2. **Неявное создание зависимостей**:
   ```python
   self.literal_parser = LiteralParser(self.adapter.tokenizer)
   self.selector = BudgetSelector(self.adapter.tokenizer)
   self.formatter = ResultFormatter(self.adapter.tokenizer, comment_style)
   ```

   Каждая стадия получает `tokenizer` в конструкторе, но это не очевидно из API.

**Рекомендации**:

- [ ] Вынести логику обработки строк в отдельный метод или компонент
- [ ] Упростить `_process_literal` до чистой координации
- [ ] Рассмотреть использование dependency injection pattern

**Оценка**: 7/10

---

#### 1.3. Стадии (`processing/*`)

##### 1.3.1. `parser.py` — LiteralParser

**Ответственность**: Парсинг структуры литералов

**Анализ API**:
```python
def parse_from_node(self, node, doc, source_text, profile) -> Optional[ParsedLiteral]
    """Высокоуровневый API: автоматически определяет параметры."""

def parse_literal_with_profile(self, text, profile, ...) -> Optional[ParsedLiteral]
    """Низкоуровневый API: требует готовых параметров."""
```

**Проблемы**:

1. **Метод `_detect_wrapper_from_profile` (строки 68-105)**:
   - Сложная логика с множеством условий
   - Обрабатывает edge cases вроде `[]string{...}` и пустых скобок `{}`
   - 37 строк в одном методе

   **Вердикт**: Логика детектирования wrapper должна быть вынесена в отдельный utility class.

2. **Метод `_extract_content` (строки 107-153)**:
   - Смешивает логику поиска opening/closing и извлечения контента
   - Дублирует логику работы со wrapper

**Рекомендации**:

- [ ] Выделить `WrapperDetector` как отдельный класс в `utils/`
- [ ] Упростить `_extract_content` через делегирование

**Оценка**: 7/10

---

##### 1.3.2. `selector.py` — BudgetSelector

**Ответственность**: Выбор элементов по бюджету

**Анализ API**:
```python
def calculate_overhead(self, ...) -> int
def select_dfs(self, elements, budget, parser, ...) -> DFSSelection
def _select_dfs_tuples(self, ...) -> DFSSelection
def _group_into_tuples(self, ...) -> List[List[Element]]
```

**Проблемы**:

1. **Метод `select_dfs` (строки 128-226)**:
   - 98 строк
   - Смешивает логику обработки tuple_size и обычного DFS
   - Сложная вложенная логика с множеством флагов

   **Вердикт**: Нарушение SRP — один метод делает слишком много.

2. **Дублирование логики между `select_dfs` и `_select_dfs_tuples`**:
   - Оба метода содержат схожую логику подсчета токенов
   - Оба проверяют `can_afford`, `must_keep`, `must_preserve`
   - ~60% кода дублируется

**Рекомендации**:

- [ ] Выделить общую логику выбора в отдельный метод `_select_elements_with_budget`
- [ ] Упростить `select_dfs` через делегирование к специализированным методам
- [ ] Рассмотреть использование Strategy pattern для tuple_size > 1

**Оценка**: 6/10

---

##### 1.3.3. `formatter.py` — ResultFormatter

**Ответственность**: Форматирование результатов

**Анализ размера**: ~500 строк — самый крупный модуль в подсистеме

**Проблемы**:

1. **Метод `_format_multiline_impl` (строки 277-391)**:
   - 114 строк
   - Смешивает логику:
     * Сбор элементов
     * Группировку по tuple_size
     * Рекурсивную обработку вложенных структур
     * Форматирование placeholder
     * Построение финального текста

   **Вердикт**: Явное нарушение SRP — метод делает минимум 5 разных вещей.

2. **Дублирование между `_format_single_line_impl` и `_format_multiline_impl`**:
   - Логика сбора элементов дублируется
   - Логика вставки placeholder дублируется
   - Логика работы с nested selections дублируется

3. **Метод `_reconstruct_element_with_nested` (строки 190-266)**:
   - 76 строк
   - Рекурсивная логика с множеством edge cases
   - Смешивает логику определения inline/multiline и форматирования

4. **Метод `_find_comment_insertion_point` (строки 125-179)**:
   - Анализ синтаксиса языка для определения места комментария
   - Должно быть в `utils/comment_placement.py`, а не в formatter

**Рекомендации**:

- [ ] Разбить `_format_multiline_impl` на 4-5 приватных методов
- [ ] Выделить общую логику форматирования в базовый метод
- [ ] Вынести логику определения позиции комментария в отдельную утилиту
- [ ] Упростить `_reconstruct_element_with_nested` через делегирование

**Оценка**: 5/10 — требует серьезного рефакторинга

---

#### 1.4. Компоненты (`components/*`)

##### 1.4.1. `ast_sequence.py` — ASTSequenceProcessor

**Ответственность**: Обработка AST-based последовательностей (C/C++ concatenated strings)

**Анализ**:
- Размер: ~180 строк
- Автономность: ✅ полная
- API: ✅ соответствует contract

**Проблемы**:

1. **Метод `process` (строки 56-181)**:
   - 125 строк в одном методе
   - Смешивает:
     * Извлечение child nodes
     * Подсчет бюджета
     * Построение результата
     * Детектирование closing delimiter

   **Вердикт**: Нарушение SRP, но для автономного компонента приемлемо.

**Рекомендации**:

- [ ] Рассмотреть разбиение на приватные методы для улучшения читаемости
- [ ] Вынести логику детектирования closing delimiter в `utils/delimiter_detection.py`

**Оценка**: 7/10

---

##### 1.4.2. `block_init.py` — BlockInitProcessor

**Ответственность**: Обработка imperative initialization блоков

**Анализ**:
- Размер: ~450 строк — второй по размеру модуль
- Автономность: ✅ полная
- Сложность: ⚠️ высокая

**Проблемы**:

1. **Метод `process` (строки 72-137)**:
   - Маршрутизация на `_process_block` vs `_process_let_group`
   - Должна быть на уровне профиля, а не внутри компонента

2. **Метод `_optimize_statement_recursive` (строки 230-319)**:
   - 89 строк
   - Реализует DFS для вложенных литералов
   - Дублирует часть логики из `selector.py`

3. **Методы `_process_block` и `_process_let_group`**:
   - Схожая структура (сбор statements → бюджетирование → форматирование)
   - ~40% кода дублируется

4. **Метод `_reconstruct_block` (строки 430-488)**:
   - Рекурсивные вызовы `_optimize_statement_recursive`
   - Сложная логика с separators и placeholder

**Рекомендации**:

- [ ] Выделить общую логику обработки между `_process_block` и `_process_let_group`
- [ ] Упростить `_optimize_statement_recursive` через делегирование к `LiteralPipeline`
- [ ] Рассмотреть разделение на два отдельных компонента: `BlockInitProcessor` и `LetGroupProcessor`

**Оценка**: 6/10

---

#### 1.5. Утилиты (`utils/*`)

##### 1.5.1. `element_parser.py` — ElementParser

**Ответственность**: Парсинг элементов внутри литералов

**Анализ**:
- Размер: ~370 строк
- API: ✅ хорошо структурирован

**Проблемы**:

1. **Метод `parse` (строки 146-232)**:
   - 86 строк
   - Сложная state machine для парсинга
   - Обрабатывает strings, brackets, separators одновременно

   **Вердикт**: Приемлемая сложность для парсера, но можно улучшить.

2. **Статический метод `collect_factory_wrappers_from_descriptor` (строки 123-174)**:
   - 51 строка
   - Извлечение wrappers из дескриптора
   - Должен быть методом `LanguageLiteralDescriptor`, а не статическим методом парсера

3. **Метод `_extract_nested_info` (строки 281-371)**:
   - 90 строк
   - Сложная логика с множеством вложенных условий
   - Обрабатывает factory wrappers, tuple elements, nested brackets

**Рекомендации**:

- [ ] Переместить `collect_factory_wrappers_from_descriptor` в `descriptor.py`
- [ ] Разбить `_extract_nested_info` на специализированные методы
- [ ] Рассмотреть использование visitor pattern для `parse`

**Оценка**: 7/10

---

##### 1.5.2. `interpolation.py` — InterpolationHandler

**Ответственность**: Обработка интерполяции в строках

**Анализ**:
- Размер: ~200 строк
- API: ✅ чистый и понятный
- Тесты: ⚠️ отсутствуют dedicated тесты

**Проблемы**:

1. **Метод `find_interpolation_regions` (строки 65-109)**:
   - Сложная state machine
   - Обрабатывает bracketed и identifier interpolation одновременно

2. **Отсутствие тестов**:
   - Интерполяция критична для корректности (Python f-strings, JS template strings)
   - Нет dedicated unit tests для `InterpolationHandler`

**Рекомендации**:

- [ ] Добавить dedicated unit tests для `InterpolationHandler`
- [ ] Документировать edge cases (вложенные скобки, escape sequences)

**Оценка**: 7/10

---

##### 1.5.3. `indentation.py` — Indentation utilities

**Анализ**:
- Размер: ~60 строк
- API: ✅ простой и понятный
- Ответственность: ✅ четкая

**Проблемы**: Не обнаружено

**Оценка**: 9/10

---

### 2. Дублирование кода

#### 2.1. Форматирование (single-line vs multiline)

**Дублирование между**:
- `ResultFormatter._format_single_line_impl`
- `ResultFormatter._format_multiline_impl`

**Что дублируется**:
- Логика сбора элементов через `_collect_element_texts`
- Логика вставки placeholder
- Логика работы с nested selections

**Рекомендация**:
- [ ] Выделить общую логику в базовый метод `_format_impl`
- [ ] Параметризовать различия (separator style, indentation)

---

#### 2.2. Выбор элементов (flat vs tuples)

**Дублирование между**:
- `BudgetSelector.select_dfs`
- `BudgetSelector._select_dfs_tuples`

**Что дублируется**:
- Логика подсчета токенов
- Проверки `can_afford`, `must_keep`, `must_preserve`
- Обработка nested selections

**Рекомендация**:
- [ ] Выделить общую логику выбора в `_evaluate_element_fit`
- [ ] Использовать Strategy pattern для tuple vs flat

---

#### 2.3. Обработка блоков

**Дублирование между**:
- `BlockInitProcessor._process_block`
- `BlockInitProcessor._process_let_group`

**Что дублируется**:
- Сбор statements
- Бюджетирование
- Вызов `_reconstruct_*` методов

**Рекомендация**:
- [ ] Выделить общий template method `_process_block_template`
- [ ] Параметризовать различия через callbacks

---

### 3. Смешение ответственности

#### 3.1. Pipeline выполняет логику стадий

**Проблема**: Метод `LiteralPipeline._process_literal` содержит:
- Вычисление overhead (должно быть в `Selector`)
- Создание псевдо-Selection для строк (должно быть в `StringProcessor`)
- Обработка интерполяции (должно быть в `InterpolationHandler`)

**Рекомендация**:
- [ ] Вынести логику обработки строк в `StringLiteralProcessor` component
- [ ] Делегировать overhead calculation в `BudgetSelector`

---

#### 3.2. Formatter анализирует синтаксис языка

**Проблема**: Метод `ResultFormatter._find_comment_insertion_point`:
- Анализирует closing brackets, semicolons, commas
- Определяет нужен ли block comment
- Это не задача formatter — это задача `CommentPlacement` utility

**Рекомендация**:
- [ ] Создать `utils/comment_placement.py`
- [ ] Переместить логику анализа синтаксиса туда

---

#### 3.3. ElementParser содержит бизнес-логику дескриптора

**Проблема**: Статический метод `collect_factory_wrappers_from_descriptor`:
- Извлекает wrappers из профилей
- Должен быть частью `LanguageLiteralDescriptor`

**Рекомендация**:
- [ ] Переместить в `descriptor.py` как метод дескриптора
- [ ] ElementParser вызывает через `descriptor.get_factory_wrappers()`

---

### 4. Неявные зависимости

#### 4.1. Tokenizer передается везде

**Проблема**: Каждая стадия получает tokenizer в конструкторе:
```python
LiteralParser(tokenizer)
BudgetSelector(tokenizer)
ResultFormatter(tokenizer, ...)
InterpolationHandler()  # не получает, но использует через callbacks
```

**Рекомендация**:
- [ ] Рассмотреть использование service locator или DI container
- [ ] Или принять как есть (explicit is better than implicit)

---

#### 4.2. BlockInitProcessor зависит от Pipeline

**Проблема**:
```python
def __init__(self, ..., process_literal_callback: ProcessLiteralCallback):
    self.process_literal_callback = process_literal_callback
```

Компонент получает callback на `Pipeline._process_literal` для обработки вложенных литералов.

**Вердикт**: Циклическая зависимость через callback.

**Рекомендация**:
- [ ] Рассмотреть использование event bus или mediator pattern
- [ ] Или принять как допустимое решение для DFS рекурсии

---

### 5. Тестовое покрытие

#### 5.1. Unit tests

**Текущее состояние**:
- ✅ Есть golden tests для 10 языков
- ✅ Есть тесты для literals indentation
- ✅ Есть тесты для literal_comment_context
- ⚠️ Отсутствуют dedicated unit tests для утилит

**Рекомендации**:

- [ ] Добавить unit tests для `InterpolationHandler`
- [ ] Добавить unit tests для `ElementParser` (парсинг edge cases)
- [ ] Добавить unit tests для `WrapperDetector` (после выделения)

---

#### 5.2. Integration tests

**Текущее состояние**:
- ✅ Golden tests покрывают интеграцию всех компонентов
- ✅ Есть тесты для разных категорий (strings, sequences, mappings, factories, blocks)

**Оценка**: 9/10

---

### 6. Производительность

#### 6.1. Кэширование

**Текущее состояние**:
- ✅ `TokenService` кэширует подсчеты токенов
- ✅ `Pipeline._get_parser_for_profile` кэширует парсеры
- ⚠️ `detect_base_indent` и `detect_element_indent` вызываются без кэша

**Рекомендация**:
- [ ] Рассмотреть кэширование indentation для одного файла
- [ ] Измерить impact через профилирование

---

#### 6.2. Множественные проходы по AST

**Проблема**: В `_process_profile`:
```python
# Первый проход: сбор AST-extraction nodes
for p in self.descriptor.profiles:
    if isinstance(p, SequenceProfile) and p.requires_ast_extraction:
        seq_nodes = context.doc.query_nodes(p.query, "lit")

# Второй проход: query для текущего профиля
nodes = context.doc.query_nodes(profile.query, "lit")
```

**Вердикт**: Каждый профиль делает отдельный query по AST.

**Рекомендация**:
- [ ] Рассмотреть предварительный сбор всех nodes одним запросом
- [ ] Измерить impact через профилирование

---

### 7. Документация

#### 7.1. Inline documentation

**Текущее состояние**:
- ✅ Есть docstrings для публичных методов
- ⚠️ Не все edge cases документированы
- ⚠️ Нет примеров использования в docstrings

**Рекомендации**:
- [ ] Добавить примеры в docstrings для сложных методов
- [ ] Документировать edge cases (empty lists, nested structures)

---

#### 7.2. Архитектурная документация

**Текущее состояние**:
- ✅ Есть `literals_architecture.md` с описанием архитектуры
- ✅ Описаны принципы разделения на модули
- ✅ Описаны потоки данных

**Оценка**: 9/10

---

### 8. Расширяемость

#### 8.1. Добавление нового языка

**Текущий процесс**:
1. Создать дескриптор в `<язык>/literals.py`
2. Определить профили
3. Опционально создать компонент

**Оценка**: ✅ Процесс прямолинейный и понятный

---

#### 8.2. Добавление нового типа профиля

**Текущий процесс**:
1. Создать класс в `patterns.py`
2. Реализовать обработку
3. Добавить в дескриптор

**Проблема**: Недостаточно документировано, какие методы нужно реализовать в стадиях.

**Рекомендация**:
- [ ] Создать гайд по добавлению новых типов профилей
- [ ] Документировать contract между профилем и стадиями

---

### 9. Приоритизация технических долгов

#### Критичные (требуют исправления в ближайшее время)

1. **Рефакторинг `ResultFormatter._format_multiline_impl`** (114 строк)
   - Нарушение SRP
   - Трудно тестировать
   - Риск при модификации

2. **Выделение общей логики в `BudgetSelector`**
   - Дублирование между `select_dfs` и `_select_dfs_tuples`
   - Усложняет добавление новых стратегий

3. **Вынос логики обработки строк из Pipeline**
   - Нарушение границы ответственности оркестратора
   - Усложняет понимание pipeline

---

#### Важные (желательно исправить в среднесрочной перспективе)

4. **Разделение `BlockInitProcessor` на два компонента**
   - Упростит понимание логики
   - Улучшит тестируемость

5. **Вынос логики определения позиции комментария**
   - Создать `utils/comment_placement.py`
   - Убрать из formatter

6. **Добавление unit tests для утилит**
   - `InterpolationHandler`
   - `ElementParser` edge cases

---

#### Низкоприоритетные (можно отложить)

7. **Оптимизация множественных проходов по AST**
   - Требует профилирования
   - Неясен реальный impact

8. **Кэширование indentation**
   - Микро-оптимизация
   - Требует измерений

9. **Улучшение документации**
   - Добавление примеров в docstrings
   - Гайд по расширению

---

### 10. Рекомендуемый план рефакторинга

#### Этап 1: Критичные исправления (1-2 недели)

**Шаг 1.1**: Рефакторинг `ResultFormatter`
```python
# Выделить методы:
def _collect_element_texts_with_dfs(...)
def _build_multiline_lines(...)
def _add_placeholder_comment(...)
def _format_impl(is_multiline, ...)  # Общая логика
```

**Шаг 1.2**: Рефакторинг `BudgetSelector`
```python
# Выделить:
def _evaluate_element_fit(elem, budget, must_keep, must_preserve) -> bool
def _process_nested_selection(elem, budget, parser) -> DFSSelection
def _select_dfs_impl(elements, budget, strategy) -> DFSSelection
```

**Шаг 1.3**: Вынести обработку строк из Pipeline
```python
# Создать:
class StringLiteralProcessor:
    def can_handle(self, profile, node, doc) -> bool
    def process(self, node, doc, source_text, profile, budget) -> TrimResult
```

---

#### Этап 2: Важные улучшения (2-3 недели)

**Шаг 2.1**: Разделение `BlockInitProcessor`
```python
# Создать:
class BlockInitProcessor  # Для Java double-brace
class LetGroupProcessor   # Для Rust let groups
```

**Шаг 2.2**: Создание `utils/comment_placement.py`
```python
class CommentPlacementAnalyzer:
    def find_insertion_point(self, text_after, comment_style) -> (int, bool)
    def format_comment(self, content, needs_block) -> str
```

**Шаг 2.3**: Добавление unit tests
- `test_interpolation_handler.py`
- `test_element_parser_edge_cases.py`

---

#### Этап 3: Низкоприоритетные улучшения (можно отложить)

**Шаг 3.1**: Профилирование и оптимизация
- Измерить impact множественных AST queries
- Измерить impact кэширования indentation

**Шаг 3.2**: Улучшение документации
- Примеры в docstrings
- Гайд по расширению

---

### 11. Метрики качества кода

| Компонент | Размер (LOC) | Сложность | SRP | Тесты | Оценка |
|-----------|--------------|-----------|-----|-------|--------|
| `pipeline.py` | 180 | Средняя | 7/10 | ✅ Golden | 7/10 |
| `parser.py` | 160 | Средняя | 7/10 | ✅ Golden | 7/10 |
| `selector.py` | 230 | Высокая | 6/10 | ✅ Golden | 6/10 |
| `formatter.py` | 500 | Высокая | 5/10 | ✅ Golden | 5/10 |
| `ast_sequence.py` | 180 | Средняя | 7/10 | ✅ Golden | 7/10 |
| `block_init.py` | 450 | Высокая | 6/10 | ✅ Golden | 6/10 |
| `element_parser.py` | 370 | Высокая | 7/10 | ✅ Golden | 7/10 |
| `interpolation.py` | 200 | Средняя | 8/10 | ⚠️ Нет | 7/10 |
| `indentation.py` | 60 | Низкая | 9/10 | ✅ Golden | 9/10 |

**Средняя оценка**: 7.0/10

---

### 12. Заключение

#### Сильные стороны архитектуры

1. **Декларативность**: Профили позволяют описывать паттерны языков без императивного кода
2. **Расширяемость**: Добавление нового языка требует только создания дескриптора
3. **Единопроходность**: Все типы литералов обрабатываются за один проход
4. **Автономность компонентов**: Четкий contract через `can_handle()`

#### Основные проблемы

1. **Нарушение SRP**: Некоторые методы делают слишком много (formatter, selector)
2. **Дублирование кода**: Схожая логика в разных методах (~40% в некоторых случаях)
3. **Смешение ответственности**: Pipeline содержит логику стадий
4. **Недостаточная факторизация**: Общий код не выделен в shared methods

#### Общая оценка качества кода: 7.0/10

**Вердикт**: Архитектура в целом здоровая, но требует рефакторинга для улучшения поддерживаемости.

---

### 13. Референсы

- `lg-cfg/adapters/literals_architecture.md` — Архитектурный дизайн
- `lg-cfg/adapters/testing_guidelines.md` — Гайд по тестированию
- `tests/adapters/` — Golden tests
- `lg/adapters/optimizations/literals/` — Исходный код

---

**Дата следующего ревью**: После завершения Этапа 1 рефакторинга

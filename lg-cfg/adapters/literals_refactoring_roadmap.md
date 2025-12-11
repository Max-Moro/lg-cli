# Дорожная карта рефакторинга Literals Optimization

Этот документ содержит поэтапный план приведения текущего кода к финальной архитектуре, описанной в `literals_architecture.md`.

## Текущее состояние (Baseline)

### Структура "как есть"

```
lg/adapters/optimizations/literals/
├── components/
│   ├── ast_sequence.py          # ✅ Остается
│   ├── block_init.py            # ✅ Остается
│   ├── budgeting.py             # ❌ Переносим в utils/
│   ├── interpolation.py         # ❌ Переносим в utils/
│   └── placeholder.py           # ❌ Сливаем с formatter
├── processing/
│   ├── pipeline.py              # 🔧 Упрощаем (~700 строк → ~250 строк)
│   ├── parser.py                # 🔧 Расширяем (добавляем методы отступов)
│   ├── selector.py              # ✅ Без изменений
│   └── formatter.py             # 🔧 Расширяем (включаем placeholder logic)
├── element_parser.py            # ❌ Переносим в utils/
└── ... (модель без изменений)
```

### Проблемы текущей структуры

1. **Ложные компоненты**: `budgeting`, `interpolation`, `placeholder` — не настоящие компоненты
2. **Раздутый pipeline**: ~700 строк с детальной логикой обработки
3. **Протекание логики**: Условия применимости компонентов в pipeline
4. **Подготовка параметров**: Pipeline готовит параметры для компонентов

---

## Этапы рефакторинга

---

### Этап 1: Создание структуры utils/ и перенос утилит

**Цель**: Выделить утилитарные модули в отдельный пакет

**Действия**:

1. **Создать пакет `utils/`**
   ```bash
   mkdir lg/adapters/optimizations/literals/utils
   touch lg/adapters/optimizations/literals/utils/__init__.py
   ```

2. **Перенести `element_parser.py` → `utils/element_parser.py`**
   - Переместить файл
   - Обновить импорты во всех использующих модулях:
     - `processing/formatter.py`
     - `processing/selector.py`
     - `components/block_init.py`

3. **Перенести `components/budgeting.py` → `utils/budgeting.py`**
   - Переместить файл
   - Обновить импорты:
     - `processing/selector.py`
     - `processing/formatter.py`

4. **Перенести `components/interpolation.py` → `utils/interpolation.py`**
   - Переместить файл
   - Обновить импорты:
     - `processing/pipeline.py`

5. **Обновить `utils/__init__.py`**
   ```python
   from .element_parser import ElementParser, Element, ParseConfig
   from .budgeting import BudgetCalculator
   from .interpolation import InterpolationHandler

   __all__ = [
       "ElementParser", "Element", "ParseConfig",
       "BudgetCalculator",
       "InterpolationHandler",
   ]
   ```

6. **Обновить `components/__init__.py`**
   - Удалить экспорты перенесенных модулей
   - Оставить только `ASTSequenceProcessor`, `BlockInitProcessor`

**Тестирование**:

**Коммит**:
```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Extract utility modules to utils/ package

- Create utils/ package for utility modules
- Move element_parser.py to utils/
- Move budgeting.py from components/ to utils/
- Move interpolation.py from components/ to utils/
- Update all imports
- components/ now contains only specialized processors

No behavioral changes, all tests pass."
```

---

### Этап 2: Слияние PlaceholderCommentFormatter с ResultFormatter

**Цель**: Устранить ложный компонент `placeholder.py`, включив его логику в formatter

**Действия**:

1. **Скопировать код из `components/placeholder.py` в `processing/formatter.py`**
   - Скопировать класс `PlaceholderCommentFormatter` внутрь `ResultFormatter`
   - Сделать его приватным вложенным классом или методами

2. **Обновить `ResultFormatter.__init__`**
   ```python
   def __init__(self, tokenizer, comment_style):
       self.tokenizer = tokenizer
       self.comment_style = comment_style
       # Убрать self.placeholder_formatter = PlaceholderCommentFormatter(...)
   ```

3. **Перенести методы внутрь `ResultFormatter`**
   ```python
   def _format_comment_for_context(self, text_after_literal, comment_content):
       """Логика из PlaceholderCommentFormatter.format_comment_for_context"""
       ...

   def _generate_comment_text(self, category_name, tokens_saved):
       """Логика из PlaceholderCommentFormatter.generate_comment_text"""
       ...
   ```

4. **Обновить вызовы в `ResultFormatter`**
   - Заменить `self.placeholder_formatter.format_comment_for_context(...)`
   - На `self._format_comment_for_context(...)`

5. **Удалить `components/placeholder.py`**

6. **Обновить `components/__init__.py`**
   - Удалить экспорт `PlaceholderCommentFormatter`

**Тестирование**:

**Коммит**:
```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Merge PlaceholderCommentFormatter into ResultFormatter

- Move placeholder formatting logic into ResultFormatter
- Remove components/placeholder.py (false component)
- Make placeholder methods private in ResultFormatter
- Update imports

No behavioral changes, all tests pass."
```

---

### Этап 3: Расширение LiteralParser методами определения отступов

**Цель**: Переместить логику определения отступов из pipeline в parser

**Действия**:

1. **Добавить статические методы в `LiteralParser`**
   ```python
   @staticmethod
   def detect_base_indent(text: str, byte_pos: int) -> str:
       """
       Определить отступ строки, содержащей литерал.

       Логика из pipeline._get_base_indent()
       """
       line_start = text.rfind('\n', 0, byte_pos)
       if line_start == -1:
           line_start = 0
       else:
           line_start += 1

       indent = ""
       for i in range(line_start, min(byte_pos, len(text))):
           if text[i] in ' \t':
               indent += text[i]
           else:
               break

       return indent

   @staticmethod
   def detect_element_indent(literal_text: str, base_indent: str) -> str:
       """
       Определить отступ элементов внутри литерала.

       Логика из pipeline._get_element_indent()
       """
       lines = literal_text.split('\n')
       if len(lines) < 2:
           return base_indent + "    "

       for line in lines[1:]:
           stripped = line.strip()
           if stripped and not stripped.startswith((']', '}', ')')):
               indent = ""
               for char in line:
                   if char in ' \t':
                       indent += char
                   else:
                       break
               if indent:
                   return indent

       return base_indent + "    "
   ```

2. **Добавить высокоуровневый метод `parse_from_node`**
   ```python
   def parse_from_node(
       self,
       node,
       doc,
       source_text: str,
       profile: P
   ) -> ParsedLiteral[P]:
       """
       Высокоуровневый API: парсит литерал с автоматическим определением параметров.

       Pipeline должен использовать этот метод вместо низкоуровневого API.
       """
       text = doc.get_node_text(node)
       start_byte, end_byte = doc.get_node_range(node)

       # Автоматически определяем отступы
       base_indent = self.detect_base_indent(source_text, start_byte)
       element_indent = self.detect_element_indent(text, base_indent)

       # Делегируем низкоуровневому методу
       return self.parse_literal_with_profile(
           text, profile, start_byte, end_byte,
           base_indent, element_indent
       )
   ```

3. **Обновить `pipeline.py` для использования нового API**
   - В `_process_literal_impl` заменить:
     ```python
     # Было:
     base_indent = self._get_base_indent(context.raw_text, start_byte)
     element_indent = self._get_element_indent(literal_text, base_indent)
     parsed = self.parser.parse_literal_with_profile(
         text, profile, start_byte, end_byte,
         base_indent, element_indent
     )

     # Стало:
     parsed = self.parser.parse_from_node(
         node, context.doc, context.raw_text, profile
     )
     ```

4. **Удалить методы `_get_base_indent` и `_get_element_indent` из `pipeline.py`**

**Тестирование**:

**Коммит**:
```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Move indent detection logic to LiteralParser

- Add detect_base_indent() static method to LiteralParser
- Add detect_element_indent() static method to LiteralParser
- Add high-level parse_from_node() method
- Remove _get_base_indent() and _get_element_indent() from pipeline
- Pipeline now uses parser's high-level API

No behavioral changes, all tests pass."
```

---

### Этап 4: Добавление can_handle() в компоненты

**Цель**: Сделать компоненты автономными, способными самостоятельно решать применимость

**Действия**:

1. **Добавить `can_handle()` в `ASTSequenceProcessor`**
   ```python
   # components/ast_sequence.py

   def can_handle(
       self,
       profile: LiteralProfile,
       node,
       doc
   ) -> bool:
       """
       Проверить, применим ли этот компонент к данному литералу.

       ASTSequenceProcessor применим только к SequenceProfile
       с флагом requires_ast_extraction=True.
       """
       return (
           isinstance(profile, SequenceProfile) and
           profile.requires_ast_extraction
       )
   ```

2. **Обновить сигнатуру `ASTSequenceProcessor.process()`**
   ```python
   def process(
       self,
       node,
       doc,
       source_text: str,
       profile: SequenceProfile,
       token_budget: int
   ) -> Optional[TrimResult]:
       """
       Полная автономная обработка AST-based последовательности.

       Компонент сам:
       - Извлекает текст из node
       - Определяет отступы
       - Парсит элементы через AST
       - Форматирует результат
       """
       text = doc.get_node_text(node)
       base_indent = self._detect_indent(source_text, node.start_byte)
       element_indent = self._detect_element_indent(text, base_indent)

       # Остальная логика без изменений
       ...
   ```

3. **Добавить приватные методы в `ASTSequenceProcessor`**
   ```python
   @staticmethod
   def _detect_indent(text: str, byte_pos: int) -> str:
       """Определить базовый отступ (копия из LiteralParser)."""
       # Скопировать логику из LiteralParser.detect_base_indent
       ...

   @staticmethod
   def _detect_element_indent(literal_text: str, base_indent: str) -> str:
       """Определить отступ элементов (копия из LiteralParser)."""
       # Скопировать логику из LiteralParser.detect_element_indent
       ...
   ```

4. **Добавить `can_handle()` в `BlockInitProcessor`**
   ```python
   # components/block_init.py

   def can_handle(
       self,
       profile: LiteralProfile,
       node,
       doc
   ) -> bool:
       """
       Проверить применимость BlockInitProcessor.

       Применим только к BlockInitProfile.
       """
       return isinstance(profile, BlockInitProfile)
   ```

5. **Обновить `BlockInitProcessor.process()` для автономности**
   - Добавить извлечение текста и определение отступов внутри
   - Сделать полностью автономным

**Тестирование**:

**Коммит**:
```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Make components autonomous with can_handle()

- Add can_handle() to ASTSequenceProcessor
- Add can_handle() to BlockInitProcessor
- Make components fully autonomous (self-contained processing)
- Components now extract data and determine parameters internally

No behavioral changes, all tests pass."
```

---

### Этап 5: Упрощение pipeline до чистого оркестратора

**Цель**: Превратить pipeline в элегантный координатор ~250 строк

**Действия**:

1. **Создать единый метод `_process_literal()`**
   ```python
   def _process_literal(
       self,
       context: ProcessingContext,
       node,
       profile: LiteralProfile,
       budget: int
   ) -> Optional[TrimResult]:
       """
       Единая точка обработки любого литерала.

       Только координация стадий и компонентов.
       """
       # Проверка специальных компонентов
       for component in self.special_components:
           if component.can_handle(profile, node, context.doc):
               return component.process(
                   node,
                   context.doc,
                   context.raw_text,
                   profile,
                   budget
               )

       # Стандартный путь через стадии
       parsed = self.parser.parse_from_node(
           node, context.doc, context.raw_text, profile
       )

       if parsed.original_tokens <= budget:
           return None

       # Выбор стратегии: строка или коллекция
       if isinstance(profile, StringProfile):
           result = self._process_string(parsed, budget)
       else:
           result = self._process_collection(parsed, budget)

       return result
   ```

2. **Упростить `_process_string()`**
   ```python
   def _process_string(
       self,
       parsed: ParsedLiteral[StringProfile],
       budget: int
   ) -> Optional[TrimResult]:
       """Обработка строк через стандартные стадии."""
       # Расчет overhead
       overhead = self._calculate_overhead(parsed, "…")
       content_budget = max(1, budget - overhead)

       # Truncation
       truncated = self.tokenizer.truncate_to_tokens(
           parsed.content, content_budget
       )

       if len(truncated) >= len(parsed.content):
           return None

       # Коррекция для интерполяции
       interpolation_handler = InterpolationHandler()
       markers = interpolation_handler.get_active_markers(
           parsed.profile, parsed.opening, parsed.content
       )
       if markers:
           truncated = interpolation_handler.adjust_truncation(
               truncated, parsed.content, markers
           )

       # Создание pseudo-selection и форматирование
       selection = self._create_string_selection(truncated, parsed)
       formatted = self.formatter.format(parsed, selection)

       return self.formatter.create_trim_result(parsed, selection, formatted)
   ```

3. **Упростить `_process_collection()`**
   ```python
   def _process_collection(
       self,
       parsed: ParsedLiteral[CollectionProfile],
       budget: int
   ) -> Optional[TrimResult]:
       """Обработка коллекций через selector + formatter."""
       parser = self._get_parser_for_profile(parsed.profile)
       elements = parser.parse(parsed.content)

       if not elements:
           return None

       # Выбор элементов
       selection = self.selector.select_dfs(
           elements, budget, parsed.profile,
           self._get_parser_for_profile,
           ...
       )

       if not selection.has_removals:
           return None

       # Форматирование
       formatted = self.formatter.format_dfs(parsed, selection, parser)

       return self._create_trim_result_dfs(parsed, selection, formatted)
   ```

4. **Удалить старые методы-роутеры**
   - Удалить `_process_sequence_node`
   - Удалить `_process_standard_collection_node`
   - Удалить `_process_block_init_node`
   - Удалить `_process_literal_impl` (заменен на `_process_literal`)

5. **Обновить `_process_strings()` и `_process_collections()`**
   - Использовать единый `_process_literal()` вместо специализированных методов

**Тестирование**:

**Коммит**:
```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Simplify pipeline to pure orchestrator

- Create unified _process_literal() method
- Remove specialized routing methods
- Delegate applicability checks to components via can_handle()
- Pipeline is now ~250 lines of pure coordination
- Clean separation: pipeline coordinates, components/stages execute

No behavioral changes, all tests pass."
```

---

## Финальная проверка

После завершения всех этапов:

### 1. Полный прогон тестов

```bash
# Все языки, все оптимизации
./scripts/test_adapters.sh all all

# Ожидание: 100+ passed, 0 failed
```

### 2. Проверка структуры

```bash
# Проверить что структура соответствует финальной архитектуре
ls -R lg/adapters/optimizations/literals/

# Ожидаемая структура:
# processing/ - 4 файла (pipeline, parser, selector, formatter)
# components/ - 2 файла (ast_sequence, block_init)
# utils/ - 3 файла (element_parser, budgeting, interpolation)
# Корень - модель (descriptor, patterns, __init__)
```

### 3. Проверка размера pipeline.py

```bash
wc -l lg/adapters/optimizations/literals/processing/pipeline.py

# Ожидание: ~250 строк (вместо ~700)
```

### 4. Проверка git статуса

```bash
git status

# Ожидание: working tree clean (все закоммичено)
```

### 5. Финальный коммит (если есть мелкие правки)

```bash
git add .
git commit -m "refactor(literals): Complete architecture refactoring

Summary of changes:
- Extracted utils/ package for utility modules
- Merged placeholder logic into ResultFormatter
- Extended LiteralParser with indent detection
- Made components autonomous with can_handle()
- Simplified pipeline to ~250 lines of coordination

Result:
- Clean architecture with clear separation of concerns
- All tests pass (100+ tests)
- No behavioral changes (backward compatible)
- Pipeline is now an elegant orchestrator"
```

---

## Метрики успеха

После завершения рефакторинга должны быть достигнуты:

### Количественные метрики

- ✅ `pipeline.py`: ~250 строк (было ~700)
- ✅ Только 2 компонента в `components/`
- ✅ 3 утилиты в `utils/`
- ✅ 100+ тестов проходят
- ✅ 0 изменений в golden files

### Качественные метрики

- ✅ Pipeline не содержит детальной логики обработки
- ✅ Компоненты автономны (can_handle + process)
- ✅ Стадии имеют высокоуровневый API
- ✅ Четкое разделение на processing/components/utils
- ✅ Легко добавлять новые компоненты и языки

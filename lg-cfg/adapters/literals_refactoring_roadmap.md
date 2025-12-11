# Дорожная карта рефакторинга Literals Optimization

Этот документ содержит план приведения кода к финальной архитектуре, описанной в `literals_architecture.md`.

---

## ✅ Выполненные этапы (Этапы 1-4)

### Этап 1: Создание структуры utils/ и перенос утилит
**Статус**: ✅ Завершен (commit 304bbec)

**Результат**:
- Создан пакет `utils/` для утилитарных модулей
- Перенесены: `element_parser.py`, `budgeting.py`, `interpolation.py`
- Обновлены все импорты в 7 модулях
- `components/` содержит только специализированные процессоры

---

### Этап 2: Слияние PlaceholderCommentFormatter с ResultFormatter
**Статус**: ✅ Завершен (commit f067fe3)

**Результат**:
- Удален ложный компонент `components/placeholder.py`
- Логика форматирования placeholder перенесена в `ResultFormatter`
- 5 методов добавлены как приватные в `ResultFormatter`
- Чистое сокращение: 122 insertions, 156 deletions

---

### Этап 3: Расширение LiteralParser методами определения отступов
**Статус**: ✅ Завершен (commit c078f04)

**Результат**:
- Добавлены статические методы: `detect_base_indent()`, `detect_element_indent()`
- Добавлен высокоуровневый API: `parse_from_node()`
- Удалены методы `_get_base_indent()` и `_get_element_indent()` из pipeline
- Pipeline использует высокоуровневый API парсера
- Чистое упрощение: 153 insertions, 82 deletions

---

### Этап 4: Добавление can_handle() в компоненты
**Статус**: ✅ Завершен (commit fe59bd2)

**Результат**:
- Компоненты стали полностью автономными
- Добавлены методы `can_handle()` в `ASTSequenceProcessor` и `BlockInitProcessor`
- Компоненты сами извлекают данные и определяют параметры
- Унифицированная сигнатура `process(node, doc, source_text, profile, token_budget)`
- Расширение функциональности: 167 insertions, 46 deletions

---

## 🚧 Текущий этап

### Этап 5: Упрощение pipeline до чистого оркестратора

**Цель**: Превратить pipeline в элегантный координатор ~250 строк (сейчас ~700)

**Текущая структура pipeline (~700 строк)**:
```
LiteralPipeline (processing/pipeline.py)
├── apply()                                 # Entry point
├── _process_strings()                      # Pass 1
├── _process_collections()                  # Pass 2
├── _process_profile()                      # Common routing
├── _process_block_init_node()             # Специализированный роутер
├── _process_sequence_node()               # Специализированный роутер
├── _process_standard_collection_node()    # Специализированный роутер
├── _process_literal_impl()                # Низкоуровневая обработка
├── _process_string()                       # String processing
├── _process_collection_dfs()              # Collection processing
├── _apply_trim_result()                   # Apply results
├── _apply_trim_result_composing()         # Apply results (composing)
└── ... вспомогательные методы
```

**Проблемы текущего pipeline**:
1. **Специализированные роутеры** (`_process_*_node`) — дублируют логику маршрутизации
2. **Низкоуровневая обработка** (`_process_literal_impl`) — смешивает координацию и логику
3. **Условия применимости** — в pipeline вместо компонентов
4. **Подготовка параметров** — pipeline готовит данные для компонентов

**Целевая структура pipeline (~250 строк)**:
```
LiteralPipeline (processing/pipeline.py)
├── apply()                          # Entry point (двухпроходная логика)
├── _process_strings()               # Pass 1 coordinator
├── _process_collections()           # Pass 2 coordinator
├── _process_profile()               # Unified profile processing
├── _process_literal()               # ⭐ ЕДИНАЯ точка обработки
│   ├── Проверка can_handle() компонентов
│   └── Роутинг на _process_string() или _process_collection()
├── _process_string()                # Simplified string processing
├── _process_collection()            # Simplified collection processing
└── _apply_result()                  # Unified result application
```

---

### Действия по Этапу 5

#### 1. Создать единый метод `_process_literal()`

**Добавить в `processing/pipeline.py` после метода `_process_profile`:**

```python
def _process_literal(
    self,
    context: ProcessingContext,
    node,
    profile: LiteralProfile,
    budget: int
) -> Optional[TrimResult]:
    """
    Unified literal processing entry point.

    Only coordinates stages and components - no detailed logic.

    Args:
        context: Processing context
        node: Tree-sitter node
        profile: Literal profile
        budget: Token budget

    Returns:
        TrimResult if optimization applied, None otherwise
    """
    # Check special components
    for component in self.special_components:
        if component.can_handle(profile, node, context.doc):
            result = component.process(
                node,
                context.doc,
                context.raw_text,
                profile,
                budget
            )
            # Handle tuple return from BlockInitProcessor
            if isinstance(result, tuple):
                trim_result, nodes_used = result
                return trim_result
            return result

    # Standard path through stages
    parsed = self.literal_parser.parse_from_node(
        node, context.doc, context.raw_text, profile
    )

    if not parsed or parsed.original_tokens <= budget:
        return None

    # Route by profile type
    if isinstance(profile, StringProfile):
        return self._process_string(parsed, budget)
    else:
        return self._process_collection(parsed, budget)
```

#### 2. Создать упрощенный `_process_string()`

**Заменить текущий метод `_process_string()` на:**

```python
def _process_string(
    self,
    parsed: ParsedLiteral[StringProfile],
    budget: int
) -> Optional[TrimResult]:
    """
    Process string literals through standard stages.

    Args:
        parsed: Parsed string literal
        budget: Token budget

    Returns:
        TrimResult if optimization applied
    """
    # Calculate overhead
    overhead = self.budget_calculator.calculate_overhead(
        parsed.opening, parsed.closing, "…",
        parsed.is_multiline, parsed.element_indent
    )
    content_budget = max(1, budget - overhead)

    # Truncate content
    truncated = self.adapter.tokenizer.truncate_to_tokens(
        parsed.content, content_budget
    )

    if len(truncated) >= len(parsed.content):
        return None

    # Adjust for interpolation
    markers = self.interpolation.get_active_markers(
        parsed.profile, parsed.opening, parsed.content
    )
    if markers:
        truncated = self.interpolation.adjust_truncation(
            truncated, parsed.content, markers
        )

    # Create pseudo-selection and format
    kept_element = Element(
        text=truncated,
        raw_text=truncated,
        start_offset=0,
        end_offset=len(truncated),
    )
    removed_element = Element(
        text="...", raw_text="...",
        start_offset=0, end_offset=0
    )

    selection = Selection(
        kept_elements=[kept_element],
        removed_elements=[removed_element],
        total_count=1,
        tokens_kept=self.adapter.tokenizer.count_text_cached(truncated),
        tokens_removed=parsed.original_tokens - self.adapter.tokenizer.count_text_cached(truncated),
    )

    # Format result
    formatted = self.formatter.format(parsed, selection)
    return self.formatter.create_trim_result(parsed, selection, formatted)
```

#### 3. Создать упрощенный `_process_collection()`

**Заменить текущий метод `_process_collection_dfs()` на `_process_collection()`:**

```python
def _process_collection(
    self,
    parsed: ParsedLiteral[CollectionProfile],
    budget: int
) -> Optional[TrimResult]:
    """
    Process collections through selector + formatter.

    Args:
        parsed: Parsed collection literal
        budget: Token budget

    Returns:
        TrimResult if optimization applied
    """
    parser = self._get_parser_for_profile(parsed.profile)
    elements = parser.parse(parsed.content)

    if not elements:
        return None

    # Calculate overhead
    placeholder = parsed.profile.placeholder_template
    overhead = self.budget_calculator.calculate_overhead(
        parsed.opening, parsed.closing, placeholder,
        parsed.is_multiline, parsed.element_indent
    )
    content_budget = max(1, budget - overhead)

    # Select elements with DFS
    selection = self.selector.select_dfs(
        elements, content_budget,
        profile=parsed.profile,
        get_parser_func=self._get_parser_for_profile,
        min_keep=parsed.profile.min_elements,
        tuple_size=parsed.profile.tuple_size if isinstance(parsed.profile, FactoryProfile) else 1,
        preserve_top_level_keys=parsed.profile.preserve_all_keys if isinstance(parsed.profile, MappingProfile) else False,
    )

    if not selection.has_removals:
        return None

    # Format result
    formatted = self.formatter.format_dfs(parsed, selection, parser)

    trimmed_tokens = self.adapter.tokenizer.count_text_cached(formatted.text)

    return TrimResult(
        trimmed_text=formatted.text,
        original_tokens=parsed.original_tokens,
        trimmed_tokens=trimmed_tokens,
        saved_tokens=parsed.original_tokens - trimmed_tokens,
        elements_kept=selection.kept_count,
        elements_removed=selection.removed_count,
        comment_text=formatted.comment,
        comment_position=formatted.comment_byte,
    )
```

#### 4. Удалить специализированные роутеры

**Удалить полностью эти методы:**
- `_process_block_init_node()`
- `_process_sequence_node()`
- `_process_standard_collection_node()`
- `_process_literal_impl()`

#### 5. Обновить `_process_profile()` для использования `_process_literal()`

**Заменить в методе `_process_profile()` вызов `processor(...)` на:**

```python
# Было:
result = processor(context, node, max_tokens, profile)

# Стало:
result = self._process_literal(context, node, profile, max_tokens)
```

И удалить параметр `processor` из сигнатуры метода.

#### 6. Упростить `_process_strings()` и `_process_collections()`

Обновить циклы обработки для использования единого `_process_literal()`.

В `_process_strings()`:
```python
# Было сложное ветвление с docstring checks
# Стало:
result = self._process_literal(context, node, profile, max_tokens)
```

В `_process_collections()`:
```python
# Было:
self._process_profile(context, profile, max_tokens, processed_strings, processor)

# Стало:
self._process_profile(context, profile, max_tokens, processed_strings)
```

#### 7. Создать единый метод применения результатов

**Объединить `_apply_trim_result()` и `_apply_trim_result_composing()` в один:**

```python
def _apply_result(
    self,
    context: ProcessingContext,
    node,
    result: TrimResult,
    original_text: str,
    use_composing: bool = False
) -> None:
    """
    Unified result application.

    Args:
        context: Processing context
        node: Tree-sitter node
        result: Trim result to apply
        original_text: Original text for metrics
        use_composing: Whether to use composing method
    """
    start_byte, end_byte = context.doc.get_node_range(node)

    if use_composing:
        context.editor.add_replacement_composing_nested(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )
    else:
        context.editor.add_replacement(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

    # Add comment if needed
    placeholder_style = self.adapter.cfg.placeholders.style
    if placeholder_style != "none" and result.comment_text:
        text_after = context.raw_text[end_byte:]
        formatted_comment, offset = self.formatter._format_comment_for_context(
            text_after, result.comment_text
        )
        context.editor.add_insertion(
            end_byte + offset,
            formatted_comment,
            edit_type="literal_comment"
        )

    # Update metrics
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))
```

---

### Тестирование Этапа 5

```bash
./scripts/test_adapters.sh literals all
# Ожидание: 100 passed
```

Финальная проверка:

```bash
# Проверить размер pipeline
wc -l lg/adapters/optimizations/literals/processing/pipeline.py
# Цель: ~250 строк (было ~700)

# Полный прогон всех тестов
./scripts/test_adapters.sh all all
# Ожидание: 100+ passed, 0 failed
```

---

### Коммит Этапа 5

```bash
git add lg/adapters/optimizations/literals/
git commit -m "refactor(literals): Simplify pipeline to pure orchestrator

- Create unified _process_literal() method
- Simplify _process_string() and _process_collection()
- Remove specialized routing methods
- Delegate applicability checks to components via can_handle()
- Pipeline is now ~250 lines of pure coordination
- Clean separation: pipeline coordinates, components/stages execute

No behavioral changes, all tests pass."
```

---

## Финальная проверка

После завершения Этапа 5:

### 1. Полный прогон тестов (если еще не был сделан)

```bash
./scripts/test_adapters.sh literals all
# Ожидание: 100+ passed, 0 failed
```

### 2. Проверка структуры

```bash
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
# Ожидание: ~250 строк (было ~700)
```

### 4. Проверка git статуса

```bash
git status
# Ожидание: working tree clean (все закоммичено)
```

---

## Метрики успеха

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

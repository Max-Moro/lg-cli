# Code Optimization Review: Public API & Function Body

Дата ревью: 2025-12-24

## Executive Summary

Подсистемы **Public API optimization** и **Function body optimization** успешно реализованы для 10 языков. Архитектура в целом хорошо структурирована и следует декларативному подходу. Однако выявлен ряд проблем, требующих внимания.

---

## 1. Выявленные проблемы

### 1.1 Дублирование кода в языковых профилях

**Severity: Medium**

Во всех 10 языках есть повторяющиеся паттерны:

```python
# Повторяется в каждом языке:
def _is_inside_class(node: Node) -> bool:
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body", ...):
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False
```

**Файлы с дублированием:**
- `python/code_profiles.py`: `_is_inside_class`
- `typescript/code_profiles.py`: `_is_inside_class`, `_is_inside_namespace`
- `javascript/code_profiles.py`: `_is_inside_class`, `_is_inside_function`
- `kotlin/code_profiles.py`: `_is_inside_class`
- `java/code_profiles.py`: `_is_inside_class`, `_is_inside_method_or_constructor`
- `scala/code_profiles.py`: `_is_inside_class`
- `cpp/code_profiles.py`: `_is_inside_class_or_struct`
- `go/code_profiles.py`: `_is_inside_function_or_method`
- `rust/code_profiles.py`: `_is_inside_impl`

**Рекомендация:** Вынести общую функцию `is_inside_container(node, container_types, boundary_types)` в `shared/utils.py`.

---

### 1.2 Дублирование ExtendedRangeNode

**Severity: Medium**

Класс `ExtendedRangeNode` (duck-typed node с расширенным range) дублируется в:
- `typescript/code_profiles.py`
- `javascript/code_profiles.py`
- `rust/code_profiles.py`

```python
class ExtendedRangeNode:
    """Duck-typed node with extended byte range."""
    def __init__(self, start_node: Node, end_node: Node):
        self.start_byte = start_node.start_byte
        self.end_byte = end_node.end_byte
        # ... остальные поля
```

**Рекомендация:** Вынести в `shared/utils.py` или `tree_sitter_support.py`.

---

### 1.3 Несогласованность именования профилей

**Severity: Low**

Некоторые языки используют разные имена для аналогичных концепций:

| Язык | Константы/Переменные | Поля класса |
|------|---------------------|-------------|
| Python | `variable` | — |
| TypeScript | `variable` | `field` |
| Go | `constant`, `variable` | `field` |
| Rust | `const`, `static` | `field` |
| Kotlin | `property` | `property` (одинаково!) |

**Рекомендация:** Унифицировать naming convention в документации, но сохранить языковую специфику где она уместна.

---

### 1.4 Отсутствие валидации профилей

**Severity: Low**

`LanguageCodeDescriptor` не валидирует профили:
- Нет проверки на дублирующиеся имена профилей
- Нет проверки на корректность Tree-sitter queries
- Нет проверки на существование parent_profile при наследовании

**Рекомендация:** Добавить метод `validate()` с lazy-вызовом при первом использовании.

---

### 1.5 Сложная логика body_range в collector.py

**Severity: Medium**

Метод `_compute_body_range` в `ElementCollector` слишком сложен:

```python
def _compute_body_range(self, func_def, body_node, profile):
    # 1. Get inner content range (excluding braces if present)
    # 2. Check for leading comments as siblings (Python, Ruby style)
    # 3. Adjust for docstring if present
    # 4. Adjust to line start ONLY for bodies that start on a new line
    # ... 50+ lines
```

Это нарушает SRP — collector должен собирать, а не вычислять сложные range.

**Рекомендация:** Вынести логику в отдельный модуль `shared/body_range.py` или дать профилю полный контроль через `body_range_computer`.

---

### 1.6 Непоследовательное использование docstring_extractor

**Severity: Low**

Не все языки с docstrings имеют `docstring_extractor`:
- ✅ Python: есть `_find_python_docstring`
- ✅ Kotlin: есть `_find_kotlin_docstring`
- ❌ Go: нет (Go doc comments идут ДО функции, не внутри)
- ❌ Rust: нет (/// comments тоже идут до функции)

Это корректное поведение, но стоит задокументировать различие: **docstring внутри тела** vs **doc comment перед функцией**.

---

### 1.7 Избыточные комментарии в C/C++ профилях

**Severity: Low**

В `c/code_profiles.py` и `cpp/code_profiles.py` много комментариев, которые просто повторяют код:

```python
# === Functions ===
# C doesn't have classes, all functions are top-level
ElementProfile(
    name="function",
    ...
```

**Рекомендация:** Оставить только non-obvious комментарии.

---

## 2. Архитектурные наблюдения

### 2.1 Положительные аспекты

✅ **Декларативный подход**: Профили позволяют описывать элементы без процедурного кода

✅ **Единый callback `is_public`**: Инкапсулирует всю visibility логику в одном месте

✅ **Кэширование collector**: `ProcessingContext.get_collector()` создаёт один раз

✅ **Разделение сбора и применения**: Collector собирает, Optimizer применяет

✅ **Языковая инкапсуляция**: Каждый язык в своём пакете `langs/<lang>/`

### 2.2 Потенциальные улучшения

**Идея 1: Базовые профили**

Создать `BaseProfiles` с общими паттернами:
```python
# shared/base_profiles.py
class BaseProfiles:
    @staticmethod
    def class_profile(is_public_fn, query="(class_declaration) @element"):
        return ElementProfile(name="class", query=query, is_public=is_public_fn)
```

**Идея 2: Profile Composition**

Вместо наследования через `parent_profile` использовать композицию:
```python
function_profile = compose_profiles(
    base_function_profile,
    with_body=True,
    with_docstring=python_docstring_extractor,
)
```

---

## 3. Технический долг

### 3.1 Приоритет: Высокий

| Проблема | Файлы | Оценка |
|----------|-------|--------|
| Дублирование `is_inside_*` | 9 файлов | 2-3 часа |
| Дублирование `ExtendedRangeNode` | 3 файла | 1 час |

### 3.2 Приоритет: Средний

| Проблема | Файлы | Оценка |
|----------|-------|--------|
| Вынос `_compute_body_range` | collector.py | 2-3 часа |
| Валидация профилей | descriptor.py | 1-2 часа |

### 3.3 Приоритет: Низкий

| Проблема | Файлы | Оценка |
|----------|-------|--------|
| Документация docstring vs doc comment | docs/ | 30 мин |
| Очистка избыточных комментариев | c/, cpp/ | 30 мин |

---

## 4. Метрики кодовой базы

### Размер модулей (lines of code)

| Модуль | LOC | Комментарий |
|--------|-----|-------------|
| `shared/collector.py` | ~280 | Основная логика |
| `shared/profiles.py` | ~90 | Чистый dataclass |
| `shared/models.py` | ~70 | Чистый dataclass |
| `shared/descriptor.py` | ~100 | С наследованием |
| `function_bodies/optimizer.py` | ~180 | Оркестрация |
| `function_bodies/trimmer.py` | ~130 | Обрезка тел |
| `public_api/optimizer.py` | ~45 | Минимальная логика |

### Размер языковых профилей

| Язык | LOC code_profiles.py |
|------|----------------------|
| Python | ~120 |
| TypeScript | ~280 |
| JavaScript | ~300 |
| Kotlin | ~280 |
| Java | ~200 |
| Scala | ~180 |
| C++ | ~240 |
| C | ~150 |
| Go | ~200 |
| Rust | ~280 |

**TypeScript и JavaScript** самые большие из-за сложной export/visibility логики и `ExtendedRangeNode`.

---

## 5. Рекомендации по рефакторингу

### Этап 1: Quick Wins (1-2 дня)

1. Вынести `ExtendedRangeNode` в `shared/utils.py`
2. Вынести `is_inside_container()` helper в `shared/utils.py`
3. Очистить избыточные комментарии в C/C++

### Этап 2: Архитектурные улучшения (3-5 дней)

1. Создать `shared/body_range.py` для логики вычисления range
2. Добавить `LanguageCodeDescriptor.validate()`
3. Документировать различия docstring vs doc comment

### Этап 3: Долгосрочные улучшения (опционально)

1. Рассмотреть BaseProfiles для уменьшения boilerplate
2. Рассмотреть Profile Composition вместо наследования

---

## 6. Заключение

Архитектура подсистем Public API и Function Body оптимизаций **хорошая**. Основные проблемы связаны с дублированием кода между языками, что естественно при поддержке 10 языков.

Рекомендуемый подход: **не трогать работающее**. Рефакторинг проводить только если:
- Добавляется новый язык (тогда вынести общий код)
- Обнаружен баг, требующий изменений в нескольких местах
- Есть конкретная задача на улучшение производительности

Текущее состояние: **Production Ready** с minor tech debt.

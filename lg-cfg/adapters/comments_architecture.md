# План рефакторинга подсистемы оптимизации комментариев

## Проблемы текущей архитектуры

### 1. Костыли и технический долг
- **Monkey-patching кеша**: `doc._go_comment_analyzer` в `go/adapter.py:87-91`
- **hasattr-проверки**: `hasattr(self.adapter, '_get_comment_analyzer')` в `comments.py:40`
- **Специальная Go-логика в универсальном оптимизаторе**: Блок `needs_group_handling` (строки 71-98)
- **Разбросанные хуки без единого интерфейса**: 5+ методов в CodeAdapter

### 2. Отсутствие единого интерфейса
Текущие методы в CodeAdapter:
- `get_comment_style()` — стиль комментариев
- `is_documentation_comment(text)` — проверка по тексту
- `is_docstring_node(node, doc)` — проверка по позиции
- `hook__extract_first_sentence(optimizer, text)` — извлечение первого предложения
- `hook__smart_truncate_comment(optimizer, text, max_tokens, tokenizer)` — обрезка

### 3. Дублирование логики
- `extract_first_sentence` есть в базовом `CommentOptimizer` и в `python/comments.py`
- `smart_truncate_comment` есть в базовом `CommentOptimizer` и в `python/comments.py`

---

## Ключевые решения (согласовано с пользователем)

1. **Структура файлов**: Полная модульность — каждый анализатор в своей языковой папке
2. **Миграция**: Полное удаление старого кода, никакой обратной совместимости
3. **API naming**: `create_comment_analyzer()` — консистентно с другими методами

---

## Предлагаемое решение

### Новый интерфейс CommentAnalyzer

Создать абстрактный базовый класс `CommentAnalyzer` в `lg/adapters/optimizations/comment_analysis.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class CommentStyle:
    """Описание стиля комментариев языка."""
    single_line: str                    # "//" или "#"
    multi_line: Tuple[str, str]         # ("/*", "*/")
    doc_markers: Tuple[str, str]        # ("/**", "*/") или ("///", "")

@dataclass
class CommentInfo:
    """Информация о комментарии после анализа."""
    node: Node
    text: str
    is_documentation: bool
    group: Optional[List[Node]] = None  # Для языков с группировкой (Go)

class CommentAnalyzer(ABC):
    """Базовый класс анализатора комментариев."""

    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc
        self._analyzed = False

    @abstractmethod
    def get_style(self) -> CommentStyle:
        """Возвращает стиль комментариев языка."""
        pass

    @abstractmethod
    def analyze_comment(self, node: Node, text: str) -> CommentInfo:
        """Анализирует отдельный комментарий."""
        pass

    def extract_first_sentence(self, text: str) -> str:
        """Извлекает первое предложение. Может быть переопределен."""
        # Базовая реализация из текущего CommentOptimizer
        pass

    def truncate_comment(self, text: str, max_tokens: int, tokenizer) -> str:
        """Обрезает комментарий с правильным закрытием. Может быть переопределен."""
        # Базовая реализация из текущего CommentOptimizer
        pass
```

### Реализации для языков (каждая в своей папке)

1. **CommentAnalyzer** (ABC) — базовый интерфейс в `lg/adapters/optimizations/comment_analysis.py`
2. **PythonCommentAnalyzer** — `lg/adapters/python/comment_analysis.py`
3. **GoCommentAnalyzer** — `lg/adapters/go/comment_analysis.py` (рефакторинг существующего)
4. **RustCommentAnalyzer** — `lg/adapters/rust/comment_analysis.py`
5. **CStyleCommentAnalyzer** — `lg/adapters/c/comment_analysis.py` (используется и для C++)
6. Остальные языки (TypeScript, Java, Kotlin, Scala, JavaScript) — используют базовую реализацию

### Изменения в CodeAdapter

```python
class CodeAdapter(BaseAdapter[C], ABC):

    @abstractmethod
    def create_comment_analyzer(self, doc: TreeSitterDocument) -> CommentAnalyzer:
        """Создает анализатор комментариев для документа."""
        pass
```

Удаляем полностью:
- `get_comment_style()` → в `CommentAnalyzer.get_style()`
- `is_documentation_comment()` → в `CommentAnalyzer.is_documentation_comment()`
- `is_docstring_node()` → в `CommentAnalyzer.is_documentation_comment()`
- `hook__extract_first_sentence()` → в `CommentAnalyzer.extract_first_sentence()`
- `hook__smart_truncate_comment()` → в `CommentAnalyzer.truncate_comment()`

### Изменения в CommentOptimizer

```python
class CommentOptimizer:
    def apply(self, context: ProcessingContext) -> None:
        # Получаем анализатор через унифицированный метод
        analyzer = self.adapter.create_comment_analyzer(context.doc)

        # Единый flow для всех языков
        for node, capture_name in context.doc.query("comments"):
            info = analyzer.analyze_comment(node, context.doc.get_node_text(node))

            # Обработка групп (Go) - теперь часть CommentInfo
            if info.group and len(info.group) > 1:
                self._process_comment_group(context, analyzer, info)
                continue

            # Стандартная обработка
            self._process_single_comment(context, analyzer, info)
```

---

## План реализации

### Этап 1: Создание базовой инфраструктуры
**Файл:** `lg/adapters/optimizations/comment_analysis.py`

Создать:
- `CommentStyle` dataclass — описание стиля комментариев
- `CommentInfo` dataclass — информация о комментарии после анализа
- `CommentAnalyzer` ABC — базовый интерфейс с:
  - `get_style() -> CommentStyle`
  - `is_documentation_comment(node, text) -> bool`
  - `get_comment_group(node) -> Optional[List[Node]]`
  - `extract_first_sentence(text) -> str`
  - `truncate_comment(text, max_tokens, tokenizer) -> str`

### Этап 2: Создание языковых анализаторов
**Новые файлы:**
- `lg/adapters/python/comment_analysis.py` — PythonCommentAnalyzer
- `lg/adapters/go/comment_analysis.py` — GoCommentAnalyzer (рефакторинг из comments.py)
- `lg/adapters/rust/comment_analysis.py` — RustCommentAnalyzer
- `lg/adapters/c/comment_analysis.py` — CStyleCommentAnalyzer (для C и C++)
- `lg/adapters/typescript/comment_analysis.py` — TypeScriptCommentAnalyzer
- `lg/adapters/java/comment_analysis.py` — JavaCommentAnalyzer
- `lg/adapters/kotlin/comment_analysis.py` — KotlinCommentAnalyzer
- `lg/adapters/scala/comment_analysis.py` — ScalaCommentAnalyzer
- `lg/adapters/javascript/comment_analysis.py` — JavaScriptCommentAnalyzer

### Этап 3: Интеграция в адаптеры
Для каждого языкового адаптера:
1. Добавить метод `create_comment_analyzer(doc) -> CommentAnalyzer`
2. Удалить старые методы: `get_comment_style`, `is_documentation_comment`, `is_docstring_node`, `hook__*`

### Этап 4: Рефакторинг CommentOptimizer
**Файл:** `lg/adapters/optimizations/comments.py`

1. Убрать `needs_group_handling` и специальную Go-логику
2. Использовать единый flow через `analyzer.is_documentation_comment()` и `analyzer.get_comment_group()`
3. Заменить `self.adapter.hook__*` на вызовы методов анализатора

### Этап 5: Очистка CodeAdapter
**Файл:** `lg/adapters/code_base.py`

Удалить методы полностью:
- `get_comment_style()` — перенести в `CommentAnalyzer.STYLE` (классовый атрибут)
- `is_documentation_comment()`
- `is_docstring_node()`
- `hook__extract_first_sentence()`
- `hook__smart_truncate_comment()`

Добавить:
- Абстрактный метод `create_comment_analyzer(doc: TreeSitterDocument) -> CommentAnalyzer`
- Property `comment_style` — делегирует к классовому атрибуту анализатора

Обновить вызовы в:
- `context.py` — использовать `adapter.comment_style`
- `budget.py` — использовать `adapter.comment_style`
- `literals/pipeline.py` — использовать `adapter.comment_style`

### Этап 6: Удаление устаревших файлов
- `lg/adapters/python/comments.py` — логика перенесена в comment_analysis.py
- `lg/adapters/rust/comments.py` — логика перенесена в comment_analysis.py
- `lg/adapters/go/comments.py` — логика перенесена в comment_analysis.py

### Этап 7: Тестирование
```bash
# Проверка комментариев для всех языков
./scripts/test_adapters.sh comments all

# Полная проверка всех оптимизаций
./scripts/test_adapters.sh all all
```

Критерий успеха: все голдены без изменений

---

## Критические файлы

### Новые файлы (создать)
```
lg/adapters/optimizations/comment_analysis.py    # Базовый интерфейс CommentAnalyzer
lg/adapters/python/comment_analysis.py           # PythonCommentAnalyzer
lg/adapters/go/comment_analysis.py               # GoCommentAnalyzer
lg/adapters/rust/comment_analysis.py             # RustCommentAnalyzer
lg/adapters/c/comment_analysis.py                # CStyleCommentAnalyzer (C и C++)
lg/adapters/typescript/comment_analysis.py       # TypeScriptCommentAnalyzer
lg/adapters/java/comment_analysis.py             # JavaCommentAnalyzer
lg/adapters/kotlin/comment_analysis.py           # KotlinCommentAnalyzer
lg/adapters/scala/comment_analysis.py            # ScalaCommentAnalyzer
lg/adapters/javascript/comment_analysis.py       # JavaScriptCommentAnalyzer
```

### Модифицируемые файлы
```
lg/adapters/optimizations/comments.py            # Рефакторинг CommentOptimizer
lg/adapters/optimizations/__init__.py            # Экспорт CommentAnalyzer
lg/adapters/code_base.py                         # Новый метод, удаление хуков
lg/adapters/python/adapter.py                    # create_comment_analyzer
lg/adapters/go/adapter.py                        # create_comment_analyzer
lg/adapters/rust/adapter.py                      # create_comment_analyzer
lg/adapters/c/adapter.py                         # create_comment_analyzer
lg/adapters/cpp/adapter.py                       # create_comment_analyzer
lg/adapters/typescript/adapter.py                # create_comment_analyzer
lg/adapters/java/adapter.py                      # create_comment_analyzer
lg/adapters/kotlin/adapter.py                    # create_comment_analyzer
lg/adapters/scala/adapter.py                     # create_comment_analyzer
lg/adapters/javascript/adapter.py                # create_comment_analyzer
lg/adapters/context.py                           # Обновить create PlaceholderManager
```

### Файлы для удаления
```
lg/adapters/python/comments.py                   # Логика в comment_analysis.py
lg/adapters/rust/comments.py                     # Логика в comment_analysis.py
lg/adapters/go/comments.py                       # Логика в comment_analysis.py
```

---

## Ожидаемые результаты

1. **Единый интерфейс** `CommentAnalyzer` для всех языков
2. **Нет monkey-patching** — кеширование внутри анализатора
3. **Нет hasattr-проверок** — полиморфизм через абстрактный метод
4. **Нет специальной логики в CommentOptimizer** — всё в анализаторах
5. **Легкое добавление новых языков** — реализовать CommentAnalyzer
6. **Backward compatibility** — все тесты проходят без изменения голденов

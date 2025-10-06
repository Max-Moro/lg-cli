# План реализации Task Context Field для Listing Generator

## Обзор архитектуры изменений

Функционал `${task}` будет реализован через плагинную архитектуру шаблонизатора. Потребуются изменения в четырех основных компонентах:

1. **CLI и RunOptions** - парсинг аргумента `--task`
2. **Новый плагин TaskPlaceholderPlugin** - обработка плейсхолдеров `${task}`
3. **Расширение системы условий** - добавление условия `task`
4. **Интеграция с TemplateContext** - передача task-текста через контекст

---

## 1. Расширение типов и RunOptions

### 1.1 Добавление поля task_text в RunOptions

**Файл:** `lg/types.py`

**Изменение:** Добавить новое опциональное поле в класс `RunOptions`

```python
@dataclass(frozen=True)
class RunOptions:
    model: ModelName = ModelName("o3")
    # Адаптивные возможности
    modes: Dict[str, str] = field(default_factory=dict)  # modeset -> mode
    extra_tags: Set[str] = field(default_factory=set)  # дополнительные теги
    # Task context
    task_text: Optional[str] = None  # текст текущей задачи из --task
```

---

## 2. Парсинг CLI аргумента --task

### 2.1 Расширение парсера аргументов

**Файл:** `lg/cli.py`

**Функция:** `_build_parser()`

**Изменения:** Добавить аргумент `--task` в общие аргументы для `render` и `report`

```python
def add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "target",
        help="ctx:<name> | sec:<name> | <name> (сначала ищется контекст, иначе секция)",
    )
    sp.add_argument(
        "--model",
        default="o3",
        help="базовая модель для статистики",
    )
    sp.add_argument(
        "--mode",
        action="append",
        metavar="MODESET:MODE",
        help="активный режим в формате 'modeset:mode' (можно указать несколько)",
    )
    sp.add_argument(
        "--tags",
        help="дополнительные теги через запятую (например: python,tests,minimal)",
    )
    # ===== ДОБАВИТЬ ЭТО =====
    sp.add_argument(
        "--task",
        metavar="TEXT|@FILE|-",
        help=(
            "текст текущей задачи: прямая строка, @file для чтения из файла, "
            "или - для чтения из stdin"
        ),
    )
```

### 2.2 Обработка значения --task в _opts()

**Файл:** `lg/cli.py`

**Функция:** `_opts()`

**Изменения:** Добавить обработку аргумента `task`

```python
def _opts(ns: argparse.Namespace) -> RunOptions:
    # Парсим режимы и теги
    modes = _parse_modes(getattr(ns, "mode", None))
    extra_tags = _parse_tags(getattr(ns, "tags", None))
    
    # ===== ДОБАВИТЬ ЭТО =====
    # Парсим task
    task_text = _parse_task(getattr(ns, "task", None))
    
    return RunOptions(
        model=ns.model,
        modes=modes,
        extra_tags=extra_tags,
        task_text=task_text,  # добавить
    )
```

### 2.3 Новая функция _parse_task()

**Файл:** `lg/cli.py`

**Новая функция:** Добавить после `_parse_tags()`

```python
def _parse_task(task_arg: Optional[str]) -> Optional[str]:
    """
    Парсит аргумент --task.
    
    Поддерживает три формата:
    - Прямая строка: "текст задачи"
    - Из файла: @path/to/file.txt
    - Из stdin: -
    
    Args:
        task_arg: Значение аргумента --task или None
        
    Returns:
        Текст задачи или None
    """
    if not task_arg:
        return None
    
    # Чтение из stdin
    if task_arg == "-":
        import sys
        content = sys.stdin.read().strip()
        return content if content else None
    
    # Чтение из файла
    if task_arg.startswith("@"):
        file_path = Path(task_arg[1:])
        if not file_path.exists():
            raise ValueError(f"Task file not found: {file_path}")
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            return content if content else None
        except Exception as e:
            raise ValueError(f"Failed to read task file {file_path}: {e}")
    
    # Прямая строка
    content = task_arg.strip()
    return content if content else None
```

**Важно:** Добавить импорт `Path` в начало файла, если его там еще нет:
```python
from pathlib import Path
```

---

## 3. Создание плагина TaskPlaceholderPlugin

### 3.1 Структура нового плагина

**Новый файл:** `lg/template/task_placeholder/__init__.py`

```python
"""
Плагин для обработки task-плейсхолдеров.

Обрабатывает:
- ${task} - простая вставка текста задачи
- ${task:prompt:"default text"} - вставка с дефолтным значением
"""

from __future__ import annotations

from .nodes import TaskNode
from .plugin import TaskPlaceholderPlugin

__all__ = ["TaskPlaceholderPlugin", "TaskNode"]
```

### 3.2 AST узел для task

**Новый файл:** `lg/template/task_placeholder/nodes.py`

```python
"""
AST узел для task-плейсхолдера.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..nodes import TemplateNode


@dataclass(frozen=True)
class TaskNode(TemplateNode):
    """
    Плейсхолдер для текста задачи ${task} или ${task:prompt:"..."}.
    
    Attributes:
        default_prompt: Дефолтное значение, если task не задан (None для простого ${task})
    """
    default_prompt: Optional[str] = None
    
    def canon_key(self) -> str:
        """Возвращает канонический ключ для кэширования."""
        if self.default_prompt:
            # Экранируем кавычки и обрезаем для читаемости
            escaped = self.default_prompt.replace('"', '\\"')[:50]
            return f'task:prompt:"{escaped}"'
        return "task"


__all__ = ["TaskNode"]
```

### 3.3 Токены для task-плейсхолдера

**Новый файл:** `lg/template/task_placeholder/tokens.py`

```python
"""
Токены для парсинга task-плейсхолдеров.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_task_token_specs() -> List[TokenSpec]:
    """
    Возвращает спецификации токенов для task-плейсхолдеров.
    """
    return [
        # Ключевое слово task
        TokenSpec(
            name="TASK_KEYWORD",
            pattern=re.compile(r'\btask\b'),
        ),
        
        # Ключевое слово prompt
        TokenSpec(
            name="PROMPT_KEYWORD",
            pattern=re.compile(r'\bprompt\b'),
        ),
        
        # Строковый литерал в двойных кавычках с escape-последовательностями
        TokenSpec(
            name="STRING_LITERAL",
            pattern=re.compile(r'"(?:[^"\\]|\\.)*"'),
        ),
    ]


__all__ = ["get_task_token_specs"]
```

### 3.4 Правила парсинга task-плейсхолдера

**Новый файл:** `lg/template/task_placeholder/parser_rules.py`

```python
"""
Правила парсинга для task-плейсхолдеров.

Обрабатывает:
- ${task}
- ${task:prompt:"default text"}
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import TaskNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext


def parse_task_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит task-плейсхолдер ${task} или ${task:prompt:"..."}.
    """
    # Проверяем начало плейсхолдера
    if not context.match("PLACEHOLDER_START"):
        return None
    
    # Сохраняем позицию для отката
    saved_position = context.position
    
    # Потребляем ${
    context.consume("PLACEHOLDER_START")
    
    # Пропускаем пробелы
    while context.match("WHITESPACE"):
        context.advance()
    
    # Проверяем ключевое слово 'task'
    if not context.match("TASK_KEYWORD"):
        context.position = saved_position
        return None
    
    # Теперь мы уверены что это task-плейсхолдер
    context.advance()  # Потребляем 'task'
    
    # Пропускаем пробелы
    while context.match("WHITESPACE"):
        context.advance()
    
    # Проверяем наличие :prompt:"..."
    default_prompt = None
    if context.match("COLON"):
        context.advance()  # Потребляем :
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем 'prompt'
        if not context.match("PROMPT_KEYWORD"):
            raise ParserError("Expected 'prompt' after ':' in task placeholder", context.current())
        context.advance()
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем :
        if not context.match("COLON"):
            raise ParserError("Expected ':' after 'prompt' in task placeholder", context.current())
        context.advance()
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем строковый литерал
        if not context.match("STRING_LITERAL"):
            raise ParserError("Expected string literal after 'prompt:' in task placeholder", context.current())
        
        string_token = context.advance()
        # Парсим строковый литерал (убираем кавычки и обрабатываем escape-последовательности)
        default_prompt = _parse_string_literal(string_token.value)
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
    
    # Потребляем }
    if not context.match("PLACEHOLDER_END"):
        raise ParserError("Expected '}' to close task placeholder", context.current())
    context.consume("PLACEHOLDER_END")
    
    return TaskNode(default_prompt=default_prompt)


def _parse_string_literal(literal: str) -> str:
    """
    Парсит строковый литерал, убирая кавычки и обрабатывая escape-последовательности.
    
    Args:
        literal: Строка вида "text" с возможными escape-последовательностями
        
    Returns:
        Обработанная строка
    """
    # Убираем окружающие кавычки
    if literal.startswith('"') and literal.endswith('"'):
        literal = literal[1:-1]
    
    # Обрабатываем escape-последовательности
    result = []
    i = 0
    while i < len(literal):
        if literal[i] == '\\' and i + 1 < len(literal):
            next_char = literal[i + 1]
            if next_char == 'n':
                result.append('\n')
            elif next_char == 't':
                result.append('\t')
            elif next_char == 'r':
                result.append('\r')
            elif next_char == '\\':
                result.append('\\')
            elif next_char == '"':
                result.append('"')
            else:
                # Неизвестная escape-последовательность - оставляем как есть
                result.append('\\')
                result.append(next_char)
            i += 2
        else:
            result.append(literal[i])
            i += 1
    
    return ''.join(result)


def get_task_parser_rules() -> List[ParsingRule]:
    """
    Возвращает правила парсинга для task-плейсхолдеров.
    """
    return [
        ParsingRule(
            name="parse_task_placeholder",
            priority=PluginPriority.PLACEHOLDER,
            parser_func=parse_task_placeholder
        )
    ]


__all__ = ["get_task_parser_rules"]
```

### 3.5 Главный класс плагина

**Новый файл:** `lg/template/task_placeholder/plugin.py`

```python
"""
Плагин для обработки task-плейсхолдеров.
"""

from __future__ import annotations

from typing import List

from .nodes import TaskNode
from .parser_rules import get_task_parser_rules
from .tokens import get_task_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ProcessingContext
from ...template import TemplateContext


class TaskPlaceholderPlugin(TemplatePlugin):
    """
    Плагин для обработки task-плейсхолдеров.
    
    Обеспечивает функциональность:
    - ${task} - простая вставка текста задачи
    - ${task:prompt:"default text"} - вставка с дефолтным значением
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Инициализирует плагин с контекстом шаблона.

        Args:
            template_ctx: Контекст шаблона для управления состоянием
        """
        super().__init__()
        self.template_ctx = template_ctx

    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "task_placeholder"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.PLACEHOLDER
    
    def initialize(self) -> None:
        """Добавляет task-специфичные токены в контекст плейсхолдеров."""
        # Добавляем токены в существующий контекст плейсхолдеров
        self.registry.register_tokens_in_context(
            "placeholder",
            ["TASK_KEYWORD", "PROMPT_KEYWORD", "STRING_LITERAL"]
        )
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для task-плейсхолдеров."""
        return get_task_token_specs()

    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга task-плейсхолдеров."""
        return get_task_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        """
        def process_task_node(processing_context: ProcessingContext) -> str:
            """Обрабатывает узел TaskNode."""
            node = processing_context.get_node()
            if not isinstance(node, TaskNode):
                raise RuntimeError(f"Expected TaskNode, got {type(node)}")
            
            # Получаем task_text из RunContext через TemplateContext
            task_text = self.template_ctx.run_ctx.options.task_text
            
            # Если task_text задан и непустой - возвращаем его
            if task_text:
                return task_text
            
            # Если task_text не задан и есть default_prompt - возвращаем его
            if node.default_prompt is not None:
                return node.default_prompt
            
            # Иначе возвращаем пустую строку
            return ""
        
        return [
            ProcessorRule(
                node_type=TaskNode,
                processor_func=process_task_node
            )
        ]


__all__ = ["TaskPlaceholderPlugin"]
```

---

## 4. Расширение системы условий

### 4.1 Добавление нового типа условия

**Файл:** `lg/conditions/model.py`

**Изменение:** Добавить новый тип условия в enum `ConditionType`

```python
class ConditionType(Enum):
    """Типы условий в системе."""
    TAG = "tag"
    TAGSET = "tagset"
    SCOPE = "scope"
    TASK = "task"  # ===== ДОБАВИТЬ ЭТО =====
    AND = "and"
    OR = "or"
    NOT = "not"
    GROUP = "group"
```

**Добавить новый класс условия после `ScopeCondition`:**

```python
@dataclass
class TaskCondition(Condition):
    """
    Условие наличия task: task
    
    Истинно, если задан непустой текст задачи через --task.
    """
    
    def get_type(self) -> ConditionType:
        return ConditionType.TASK
    
    def _to_string(self) -> str:
        return "task"
```

**Обновить тип `AnyCondition` в конце файла:**

```python
# Объединенный тип для всех условий
AnyCondition = Union[
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    TaskCondition,  # ===== ДОБАВИТЬ ЭТО =====
    GroupCondition,
    NotCondition,
    BinaryCondition,
]
```

**Обновить `__all__` в конце файла:**

```python
__all__ = [
    "Condition",
    "ConditionType",
    "TagCondition",
    "TagSetCondition",
    "ScopeCondition",
    "TaskCondition",  # ===== ДОБАВИТЬ ЭТО =====
    "GroupCondition",
    "NotCondition",
    "BinaryCondition",
]
```

### 4.2 Расширение лексера условий

**Файл:** `lg/conditions/lexer.py`

**Изменение:** Добавить 'task' в список ключевых слов

```python
# Ключевые слова для постпроцессинга
KEYWORDS = {
    'TAGSET', 'scope', 'tag', 'task', 'AND', 'OR', 'NOT'  # ===== ДОБАВИТЬ 'task' =====
}
```

### 4.3 Расширение парсера условий

**Файл:** `lg/conditions/parser.py`

**Изменение:** Добавить импорт `TaskCondition` в начало файла

```python
from .model import (
    Condition,
    ConditionType,
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    TaskCondition,  # ===== ДОБАВИТЬ ЭТО =====
    GroupCondition,
    NotCondition,
    BinaryCondition,
)
```

**Добавить обработку в метод `_parse_primary()` класса `ConditionParser`:**

```python
def _parse_primary(self) -> Condition:
    """Парсит первичное выражение (атомарные условия и группы в скобках)."""
    # Группировка в скобках
    if self._match_symbol("("):
        expr = self._parse_expression()
        if not self._match_symbol(")"):
            raise ParseError("Expected ')' after grouped expression", self._current_position())
        return GroupCondition(condition=expr)
    
    # tag:name
    if self._match_keyword("tag"):
        return self._parse_tag_condition()
    
    # TAGSET:set:tag
    if self._match_keyword("TAGSET"):
        return self._parse_tagset_condition()
    
    # scope:type
    if self._match_keyword("scope"):
        return self._parse_scope_condition()
    
    # ===== ДОБАВИТЬ ЭТО =====
    # task (условие без параметров)
    if self._match_keyword("task"):
        return TaskCondition()
    # ===== КОНЕЦ ДОБАВЛЕНИЯ =====
    
    # Если ничего не подошло, это ошибка
    current = self._current_token()
    if current.type == 'EOF':
        raise ParseError("Unexpected end of expression", current.position)
    else:
        raise ParseError(f"Unexpected token '{current.value}'", current.position)
```

### 4.4 Расширение evaluator условий

**Файл:** `lg/conditions/evaluator.py`

**Изменение:** Добавить импорт `TaskCondition`

```python
from .model import (
    Condition,
    ConditionType,
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    TaskCondition,  # ===== ДОБАВИТЬ ЭТО =====
    GroupCondition,
    NotCondition,
    BinaryCondition,
)
```

**Добавить обработку в метод `evaluate()` класса `ConditionEvaluator`:**

```python
def evaluate(self, condition: Condition) -> bool:
    """
    Вычисляет значение условия.

    Args:
        condition: Корневой узел AST условия

    Returns:
        Булево значение результата вычисления

    Raises:
        EvaluationError: При ошибке вычисления (например, неизвестный тип условия)
    """
    condition_type = condition.get_type()

    if condition_type == ConditionType.TAG:
        return self._evaluate_tag(cast(TagCondition, condition))
    elif condition_type == ConditionType.TAGSET:
        return self._evaluate_tagset(cast(TagSetCondition, condition))
    elif condition_type == ConditionType.SCOPE:
        return self._evaluate_scope(cast(ScopeCondition, condition))
    # ===== ДОБАВИТЬ ЭТО =====
    elif condition_type == ConditionType.TASK:
        return self._evaluate_task(cast(TaskCondition, condition))
    # ===== КОНЕЦ ДОБАВЛЕНИЯ =====
    elif condition_type == ConditionType.GROUP:
        return self._evaluate_group(cast(GroupCondition, condition))
    elif condition_type == ConditionType.NOT:
        return self._evaluate_not(cast(NotCondition, condition))
    elif condition_type == ConditionType.AND:
        return self._evaluate_and(cast(BinaryCondition, condition))
    elif condition_type == ConditionType.OR:
        return self._evaluate_or(cast(BinaryCondition, condition))
    else:
        raise EvaluationError(f"Unknown condition type: {condition_type}")
```

**Добавить новый метод `_evaluate_task()` после `_evaluate_scope()`:**

```python
def _evaluate_task(self, condition: TaskCondition) -> bool:
    """
    Вычисляет условие task.

    Истинно, если задан непустой текст задачи.
    """
    return self.context.is_task_provided()
```

### 4.5 Расширение ConditionContext

**Файл:** `lg/run_context.py`

**Добавить новый метод в класс `ConditionContext`:**

```python
@dataclass
class ConditionContext:
    """
    Контекст для вычисления условий.
    """
    active_tags: Set[str]
    tagsets: Dict[str, Set[str]]
    origin: str
    task_text: Optional[str] = None  # ===== ДОБАВИТЬ ЭТО =====
    
    # ... существующие методы ...
    
    # ===== ДОБАВИТЬ ЭТОТ МЕТОД =====
    def is_task_provided(self) -> bool:
        """
        Проверяет, задан ли непустой текст задачи.
        
        Returns:
            True если task_text не None и не пустая строка
        """
        return bool(self.task_text and self.task_text.strip())
```

### 4.6 Обновление создания ConditionContext в TemplateContext

**Файл:** `lg/template/context.py`

**Изменение:** Обновить метод `_create_condition_context()`

```python
def _create_condition_context(self) -> ConditionContext:
    """Создает контекст условий из текущего состояния шаблона."""
    tagsets = self._get_tagsets()
    
    # ===== ДОБАВИТЬ task_text =====
    return ConditionContext(
        active_tags=self.current_state.active_tags,
        tagsets=tagsets,
        origin=self.current_state.origin,
        task_text=self.run_ctx.options.task_text,  # ДОБАВИТЬ ЭТО
    )
```

---

## 5. Регистрация нового плагина

### 5.1 Регистрация в TemplateProcessor

**Файл:** `lg/template/processor.py`

**Функция:** `create_template_processor()`

**Изменение:** Добавить регистрацию нового плагина

```python
def create_template_processor(run_ctx: RunContext) -> TemplateProcessor:
    """
    Создает процессор шаблонов с уже установленными доступными плагинами.
    
    Args:
        run_ctx: Контекст выполнения
        
    Returns:
        Настроенный процессор шаблонов
    """
    # Создаем новый реестр для этого процессора
    registry = TemplateRegistry()
    
    # Создаем процессор (обработчики настроятся автоматически в конструкторе)
    processor = TemplateProcessor(run_ctx, registry)
    
    # Регистрируем доступные плагины (в порядке приоритета)
    from .common_placeholders import CommonPlaceholdersPlugin
    from .adaptive import AdaptivePlugin
    from .md_placeholders import MdPlaceholdersPlugin
    from .task_placeholder import TaskPlaceholderPlugin  # ===== ДОБАВИТЬ ЭТО =====
    
    registry.register_plugin(CommonPlaceholdersPlugin(processor.template_ctx))
    registry.register_plugin(AdaptivePlugin(processor.template_ctx))
    registry.register_plugin(MdPlaceholdersPlugin(processor.template_ctx))
    registry.register_plugin(TaskPlaceholderPlugin(processor.template_ctx))  # ===== ДОБАВИТЬ ЭТО =====
    
    # Инициализируем плагины после регистрации всех компонентов
    registry.initialize_plugins(processor.handlers)

    return processor
```

---

## 6. Тестирование

### 6.1 Минимальный тестовый сценарий

Создать тестовые файлы для проверки работоспособности:

**Тестовый шаблон:** `lg-cfg/test-task.ctx.md`

```markdown
# Контекст разработки

## Исходный код
${src-core}

## Текущая задача

${task:prompt:"Задача не указана. Просто подтверди, что прочитал."}

{% if task %}
---
**Важно:** Сконцентрируйся на описанной задаче!
{% endif %}
```

**Команды для тестирования:**

```bash
# Тест 1: без --task (должен использовать дефолтное значение)
lg render ctx:test-task

# Тест 2: с прямой строкой
lg render ctx:test-task --task "Реализовать кеширование"

# Тест 3: из stdin
echo "Исправить баг #123" | lg render ctx:test-task --task -

# Тест 4: из файла
echo "Добавить новый API endpoint" > .current-task.txt
lg render ctx:test-task --task @.current-task.txt

# Тест 5: условие {% if task %}
lg render ctx:test-task  # не должно быть "Важно:"
lg render ctx:test-task --task "Test"  # должно быть "Важно:"
```

---

## 7. Чек-лист реализации

### Порядок внесения изменений:

1. ✅ **Типы и RunOptions** (`lg/types.py`)
   - Добавить `task_text: Optional[str]` в `RunOptions`

2. ✅ **CLI** (`lg/cli.py`)
   - Добавить аргумент `--task` в `_build_parser()`
   - Добавить функцию `_parse_task()`
   - Обновить `_opts()` для обработки task

3. ✅ **Система условий** (`lg/conditions/`)
   - Добавить `TaskCondition` в `model.py`
   - Добавить 'task' в keywords в `lexer.py`
   - Добавить парсинг `task` в `parser.py`
   - Добавить `_evaluate_task()` в `evaluator.py`
   - Добавить `is_task_provided()` в `run_context.py`
   - Обновить `_create_condition_context()` в `template/context.py`

4. ✅ **Плагин TaskPlaceholder** (`lg/template/task_placeholder/`)
   - Создать `__init__.py`
   - Создать `nodes.py` с `TaskNode`
   - Создать `tokens.py` с токенами
   - Создать `parser_rules.py` с правилами парсинга
   - Создать `plugin.py` с главным классом

5. ✅ **Регистрация плагина** (`lg/template/processor.py`)
   - Импортировать и зарегистрировать `TaskPlaceholderPlugin`

6. ✅ **Тестирование**
   - Создать тестовый шаблон
   - Проверить все сценарии использования

---

## 8. Важные замечания по реализации

### 8.1 Приоритет плагина

`TaskPlaceholderPlugin` должен иметь приоритет `PluginPriority.PLACEHOLDER` (90), что ставит его на один уровень с `CommonPlaceholdersPlugin` и `MdPlaceholdersPlugin`. Это корректно, так как все они обрабатывают плейсхолдеры вида `${...}`.

### 8.2 Обработка пустых значений

- Пустая строка из `--task ""` эквивалентна отсутствию аргумента
- `${task}` без дефолта → пустая строка
- `${task:prompt:"..."}` без task → дефолтное значение
- Условие `{% if task %}` проверяет наличие непустого текста

### 8.3 Escape-последовательности

Функция `_parse_string_literal()` обрабатывает:
- `\n` → новая строка
- `\t` → табуляция
- `\\` → обратный слэш
- `\"` → кавычка
- Другие escape-последовательности сохраняются как есть

### 8.4 Интеграция с существующими условиями

Условие `task` полностью совместимо с существующими:
- `{% if task AND tag:review %}` - работает
- `{% if NOT task OR tag:minimal %}` - работает
- Группировка через скобки - работает

---

## 9. Возможные расширения (будущее)

### 9.1 Дополнительные параметры task

В будущем можно добавить:
- `${task:maxlen:500}` - ограничение длины
- `${task:format:markdown}` - форматирование

### 9.2 Множественные задачи

Поддержка нескольких задач через индексы:
- `${task}` - первая задача
- `${task:1}` - вторая задача
- `--task "Task 1" --task "Task 2"`

Но это выходит за рамки текущего ТЗ.

---

## Итог

План реализации покрывает все требования ТЗ:
- ✅ CLI аргумент `--task` с поддержкой трех форматов
- ✅ Плейсхолдер `${task}` с дефолтным значением
- ✅ Условие `{% if task %}`
- ✅ Комбинирование с другими условиями
- ✅ Обратная совместимость

Реализация следует архитектуре LG через плагинную систему и не ломает существующий код.
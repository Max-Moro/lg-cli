# ТЗ: Task Context Field — CLI Implementation

## Обзор

Добавление поддержки динамического контекста текущей задачи через CLI-аргумент `--task` и специальный плейсхолдер `${task}` в шаблонах.

## Цель

Позволить пользователям добавлять финальные инструкции и описание текущей задачи к сгенерированному контексту без необходимости редактирования файлов шаблонов.

---

## 1. CLI Аргумент `--task`

### Синтаксис

```bash
lg render ctx:dev --task "Описание текущей задачи"
lg report ctx:dev --task "Описание текущей задачи"
```

### Варианты использования

#### 1.1 Прямая строка
```bash
lg render ctx:dev --task "Реализовать кеширование результатов"
```

#### 1.2 Многострочный текст через stdin
```bash
echo -e "Задача:\n- Исправить баг #123\n- Добавить тесты" | lg render ctx:dev --task -
```

#### 1.3 Из файла
```bash
lg render ctx:dev --task @.current-task.txt
```

### Поведение

- Если `--task` не указан, плейсхолдер `${task}` рендерится пустой строкой
- Если указан `--task -`, читать из stdin до EOF
- Если указан `--task @path`, читать содержимое файла
- Пустая строка эквивалентна отсутствию аргумента

---

## 2. Плейсхолдер `${task}` в шаблонах

### 2.1 Простой плейсхолдер

**Синтаксис:**
```markdown
${task}
```

**Поведение:**
- Если `--task` задан и непустой → подставляется значение как есть
- Если `--task` пустой или не задан → подставляется пустая строка (не удаляется строка, просто пустое значение)

**Пример шаблона:**
```markdown
# Контекст разработки

${tpl:intro}
${src-core}

## Текущая задача

${task}
```

**Результат без --task:**
```markdown
# Контекст разработки

[содержимое intro]
[содержимое src-core]

## Текущая задача


```

**Результат с --task:**
```markdown
# Контекст разработки

[содержимое intro]
[содержимое src-core]

## Текущая задача

Реализовать кеширование результатов
```

### 2.2 Плейсхолдер с дефолтным значением

**Синтаксис:**
```markdown
${task:prompt:"Дефолтный текст"}
```

**Поведение:**
- Если `--task` задан и непустой → подставляется значение из аргумента
- Если `--task` пустой или не задан → подставляется дефолтное значение из `prompt:`

**Пример:**
```markdown
${task:prompt:"Ничего пока делать не нужно. Просто подтверди, что ты дочитал досюда."}
```

**Результат без --task:**
```markdown
Ничего пока делать не нужно. Просто подтверди, что ты дочитал досюда.
```

**Результат с --task "Fix bug #123":**
```markdown
Fix bug #123
```

### 2.3 Синтаксис дефолтного значения

Формат: `${task:prompt:"текст"}`

**Правила парсинга:**
- Ключевое слово `prompt:` обязательно
- Значение заключено в двойные кавычки `"`
- Внутри строки поддерживаются escape-последовательности: `\"`, `\\`, `\n`
- Пробелы вокруг `prompt:` игнорируются

**Примеры валидных форм:**
```markdown
${task:prompt:"Simple text"}
${task:prompt: "Text with spaces"  }
${task:prompt:"Text with \"quotes\""}
${task:prompt:"Multiline\ntext\nhere"}
```

---

## 3. Условные конструкции

### 3.1 Проверка наличия task

**Синтаксис:**
```markdown
{% if task %}
содержимое
{% endif %}
```

**Поведение:**
- Блок включается, только если `--task` задан и непустой
- Поддерживает вложенность с другими условиями через `AND`, `OR`, `NOT`

**Пример:**
```markdown
# Контекст разработки

${tpl:intro}
${src-core}

{% if task %}
## Описание текущей задачи

${task}
{% endif %}
```

**Результат без --task:**
```markdown
# Контекст разработки

[содержимое intro]
[содержимое src-core]
```

**Результат с --task:**
```markdown
# Контекст разработки

[содержимое intro]
[содержимое src-core]

## Описание текущей задачи

Реализовать кеширование результатов
```

### 3.2 Комбинирование условий

```markdown
{% if task AND tag:review %}
## Задача для ревью

${task}
{% endif %}

{% if NOT task %}
_Конкретная задача не указана. Общий обзор:_
{% endif %}
```

---

## 4. Технические детали реализации

### 4.1 Расширение RunOptions

```python
@dataclass(frozen=True)
class RunOptions:
    model: ModelName = ModelName("o3")
    modes: Dict[str, str] = field(default_factory=dict)
    extra_tags: Set[str] = field(default_factory=set)
    task: Optional[str] = None  # <-- НОВОЕ ПОЛЕ
```

### 4.2 Парсинг CLI аргумента

```python
def _parse_task_argument(task_arg: Optional[str]) -> str:
    """
    Парсит значение --task аргумента.
    
    Returns:
        - Пустая строка если task_arg is None
        - Содержимое stdin если task_arg == "-"
        - Содержимое файла если task_arg.startswith("@")
        - Сам task_arg в остальных случаях
    """
    if task_arg is None:
        return ""
    
    if task_arg == "-":
        return sys.stdin.read()
    
    if task_arg.startswith("@"):
        path = Path(task_arg[1:])
        if not path.exists():
            raise ValueError(f"Task file not found: {path}")
        return path.read_text(encoding="utf-8")
    
    return task_arg
```

### 4.3 Контекст шаблонизации

Добавить в `TemplateContext`:

```python
class TemplateContext:
    # ... существующие поля
    
    @property
    def task(self) -> str:
        """Текущее значение task из RunOptions."""
        return self.run_ctx.options.task or ""
    
    def has_task(self) -> bool:
        """Проверка наличия непустого task."""
        return bool(self.task.strip())
```

### 4.4 Плейсхолдеры в шаблонизаторе

Добавить обработку в `lg/template/processor.py`:

```python
def resolve_placeholder(self, placeholder: str) -> str:
    # ... существующая логика для sec:, ctx:, tpl:, md:
    
    # Обработка ${task}
    if placeholder == "task":
        return self.template_ctx.task
    
    # Обработка ${task:prompt:"..."}
    if placeholder.startswith("task:prompt:"):
        if self.template_ctx.has_task():
            return self.template_ctx.task
        else:
            # Парсинг дефолтного значения
            default = self._parse_task_prompt_default(placeholder)
            return default
    
    # ... остальная логика
```

### 4.5 Условные выражения

Добавить в `lg/conditions/evaluator.py`:

```python
def evaluate_condition(expr: str, ctx: TemplateContext) -> bool:
    # ... существующая логика
    
    # Специальный case для "task"
    if expr.strip() == "task":
        return ctx.has_task()
    
    # ... остальная логика
```

---

## 5. Обратная совместимость

- Старые шаблоны без `${task}` продолжают работать как прежде
- `--task` опционален, его отсутствие не ломает существующие команды
- Плейсхолдер `${task}` в шаблонах игнорируется, если аргумент не передан

---

## 6. Примеры использования

### Пример 1: Простой контекст с задачей

**Шаблон `lg-cfg/dev.ctx.md`:**
```markdown
# Development Context

${src-core}
${tests}

## Current Task

${task}
```

**Команда:**
```bash
lg render ctx:dev --task "Implement caching for expensive operations"
```

### Пример 2: Условное включение секции

**Шаблон `lg-cfg/review.ctx.md`:**
```markdown
# Code Review Context

${tpl:intro}
${src-changed}

{% if task %}
## Review Focus

${task}
{% else %}
_No specific focus specified. General review._
{% endif %}
```

**Команда без task:**
```bash
lg render ctx:review
# → Выведет "No specific focus specified. General review."
```

**Команда с task:**
```bash
lg render ctx:review --task "Focus on error handling in HTTP layer"
# → Выведет секцию "Review Focus" с текстом задачи
```

### Пример 3: Дефолтное значение

**Шаблон `lg-cfg/ask.ctx.md`:**
```markdown
# Q&A Context

${docs}
${api-reference}

## Question

${task:prompt:"Ничего конкретного не спрашиваю. Просто подтверди, что контекст загружен."}
```

**Команда без task:**
```bash
lg render ctx:ask
# → Подставит дефолтное сообщение
```

**Команда с task:**
```bash
lg render ctx:ask --task "How to implement custom authentication?"
# → Подставит вопрос пользователя
```

---

## 7. Тестовые сценарии

### 7.1 Unit-тесты

```python
def test_task_placeholder_empty():
    """${task} рендерится пустой строкой без --task"""
    
def test_task_placeholder_with_value():
    """${task} подставляет значение из --task"""
    
def test_task_prompt_default():
    """${task:prompt:"default"} использует дефолт без --task"""
    
def test_task_prompt_override():
    """${task:prompt:"default"} использует --task если задан"""
    
def test_task_condition_true():
    """{% if task %} включается при наличии --task"""
    
def test_task_condition_false():
    """{% if task %} исключается без --task"""
    
def test_task_from_stdin():
    """--task - читает из stdin"""
    
def test_task_from_file():
    """--task @file читает из файла"""
```

### 7.2 Интеграционные тесты

```python
def test_render_context_with_task():
    """Полный цикл: render контекста с --task"""
    
def test_report_with_task():
    """report учитывает --task в статистике"""
    
def test_nested_conditions_with_task():
    """Комбинации task с другими условиями"""
```

---

## 8. Документация

### 8.1 Обновить README.md

Добавить секцию "Task Context" с примерами использования `--task`.

### 8.2 Обновить docs/templates.md

Добавить описание плейсхолдеров `${task}` и `${task:prompt:"..."}`.

### 8.3 Обновить docs/adaptability.md

Добавить `task` в список доступных условных операторов.

---

## 9. Приоритеты реализации

1. **P0 (Must have):**
   - Парсинг `--task` аргумента
   - Простой плейсхолдер `${task}`
   - Условие `{% if task %}`

2. **P1 (Should have):**
   - Плейсхолдер с дефолтом `${task:prompt:"..."}`
   - Чтение из stdin (`--task -`)
   - Чтение из файла (`--task @file`)

3. **P2 (Nice to have):**
   - Escape-последовательности в prompt
   - Интеграция с `report` командой

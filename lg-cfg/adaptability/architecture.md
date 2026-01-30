# Архитектура подсистемы адаптивных возможностей

## Обзор

Подсистема адаптивных возможностей (Adaptive System) обеспечивает контекстно-зависимую конфигурацию генерируемых контекстов через систему **режимов** (modes) и **тегов** (tags). Архитектура построена на принципе **контекстной зависимости**: доступные режимы и теги определяются не глобально, а вычисляются для каждого контекста на основе используемых в нём секций.

## Ключевые архитектурные решения

### Децентрализованное хранение конфигурации

Режимы и теги объявляются **внутри секций** (`sections.yaml`, `*.sec.yaml`), а не в отдельных глобальных файлах. Это решение обеспечивает:
- высокую связность: конфигурация режимов находится рядом с контентом, на который она влияет;
- возможность переиспользования через наследование (`extends`);
- изоляцию между разными контекстами.

### Разделение на интеграционные и контентные наборы режимов

**Интеграционный набор** (integration mode-set) содержит `runs` — параметры запуска AI-провайдеров. **Контентный набор** не содержит `runs` и влияет только на формирование контента.

**Инвариант**: после резолва адаптивной модели для контекста должен существовать **ровно один** интеграционный набор режимов. Это гарантирует однозначность параметров запуска при нажатии "Send to AI" в IDE-плагинах.

### Ленивое вычисление модели

Адаптивная модель вычисляется **только при необходимости** — во время `render`/`report` или `list mode-sets`/`list tag-sets`. Это позволяет избежать парсинга всех секций при каждом запуске CLI.

---

## Структура пакетов

```
lg/
├── adaptive/              # Ядро адаптивной системы
│   ├── model.py           # Модели данных
│   ├── context_resolver.py # Оркестратор резолва для контекстов
│   ├── extends_resolver.py # Резолв цепочек наследования
│   ├── section_extractor.py # Извлечение модели из SectionCfg
│   ├── validation.py      # Бизнес-правила валидации
│   ├── listing.py         # CLI-команды list
│   └── errors.py          # Типизированные ошибки
│
├── conditions/            # Система условий ({% if %}, when:)
│   ├── model.py           # AST условий
│   ├── parser.py          # Парсер строковых условий
│   ├── lexer.py           # Лексер
│   └── evaluator.py       # Вычислитель условий
│
├── template/
│   ├── context.py         # TemplateContext — состояние рендеринга
│   ├── evaluator.py       # Обёртка над conditions для шаблонов
│   ├── frontmatter.py     # Парсер YAML frontmatter
│   ├── adaptive/          # Плагин для {% if %}, {% mode %}
│   └── analysis/
│       └── section_collector.py  # Сбор секций без рендеринга
│
├── section/
│   ├── model.py           # SectionCfg с полями extends, mode-sets, tag-sets
│   ├── service.py         # SectionService для поиска и загрузки секций
│   └── index.py           # Индексирование секций в скоупе
│
├── addressing/
│   ├── types.py           # ResolvedSection с current_dir для extends
│   ├── context.py         # AddressingContext — стек директорий
│   └── section_resolver.py # Резолв секций через AddressingContext
│
└── run_context.py         # ConditionContext для оценки условий
```

---

## Модели данных (`lg/adaptive/model.py`)

### Иерархия типов

```
AdaptiveModel
├── mode_sets: Dict[str, ModeSet]
│   └── ModeSet
│       ├── id, title
│       ├── modes: Dict[str, Mode]
│       │   └── Mode
│       │       ├── id, title, description
│       │       ├── tags: List[str]
│       │       ├── default_task: Optional[str]
│       │       ├── vcs_mode: "all" | "changes" | "branch-changes"
│       │       └── runs: Dict[str, str]  # provider_id → args
│       └── is_integration: bool  # computed
│
└── tag_sets: Dict[str, TagSet]
    └── TagSet
        ├── id, title
        └── tags: Dict[str, Tag]
            └── Tag: id, title, description
```

### Ключевые методы AdaptiveModel

- `merge_with(other)` — детерминированный мердж двух моделей (используется при extends)
- `filter_by_provider(provider_id)` — фильтрация интеграционного набора по провайдеру
- `validate_single_integration()` — проверка инварианта единственного интеграционного набора
- `get_integration_mode_set()` — получение единственного интеграционного набора

### Универсальный провайдер `clipboard`

Константа `CLIPBOARD_PROVIDER = "clipboard"` обозначает особый провайдер, который **неявно совместим со всеми режимами**. Метод `Mode.has_provider("clipboard")` всегда возвращает `True`. Это позволяет копировать контекст для ручной вставки в любой AI-инструмент.

---

## Резолв адаптивной модели

### Потоки данных

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ContextResolver                              │
│                                                                      │
│  1. SectionCollector                                                 │
│     ├── Парсит шаблон контекста в AST                               │
│     ├── Обходит все узлы (включая ветки {% if %})                   │
│     ├── Собирает ResolvedSection для каждого ${section}             │
│     └── Добавляет секции из frontmatter include                     │
│                                                                      │
│  2. ExtendsResolver (для каждой секции)                             │
│     ├── Разворачивает extends depth-first, left-to-right            │
│     ├── Детектирует циклы через стек резолва                        │
│     └── Мерджит конфигурации (child wins)                           │
│                                                                      │
│  3. Merge all sections                                               │
│     ├── Порядок: секции из шаблона, затем frontmatter               │
│     └── AdaptiveModel.merge_with()                                   │
│                                                                      │
│  4. Validation                                                       │
│     └── validate_single_integration()                                │
└─────────────────────────────────────────────────────────────────────┘
```

### ContextResolver (`lg/adaptive/context_resolver.py`)

Оркестратор, координирующий полный резолв адаптивной модели для контекста.

**Входные данные**:
- `context_name` — имя контекста (без `.ctx.md`)

**Зависимости**:
- `SectionService` — поиск и загрузка секций
- `AddressingContext` — резолв адресных ссылок (`@scope:section`)
- `SectionCollector` — сбор секций из шаблона
- `ExtendsResolver` — резолв наследования

**Результат**: `ContextAdaptiveData` с полной моделью и метаданными.

**Кеширование**: результаты кешируются по `context_name` для повторных обращений в рамках одного запуска.

### ExtendsResolver (`lg/adaptive/extends_resolver.py`)

Резолвит цепочки наследования секций с детекцией циклов.

**Алгоритм**:
1. Если секция в стеке резолва — цикл, бросаем `ExtendsCycleError`
2. Для каждого parent в `extends` (слева направо):
   - Рекурсивно резолвим parent
   - Мерджим результат в аккумулятор
3. Применяем локальную конфигурацию секции (child wins)

**Что мерджится**:
- `mode_sets`, `tag_sets` (через `AdaptiveModel.merge_with`)
- `extensions`, `adapters`, `skip_empty`, `path_labels`

**Что НЕ мерджится**:
- `filters`, `targets` — они принадлежат только конечной секции

### SectionCollector (`lg/template/analysis/section_collector.py`)

Собирает все секции, используемые в контексте, **без выполнения рендеринга**.

**Особенности**:
- Обходит ветки `{% if %}` без оценки условий — все секции учитываются
- Исключает `${md:...}` — они не содержат mode-sets/tag-sets
- Обрабатывает транзитивные include (`${tpl:...}`, `${ctx:...}`)
- Детектирует циклические include

---

## Связь с подсистемой адресации

### Проблема контекста директорий

При обработке шаблонов `AddressingContext` поддерживает стек директорий, который позволяет корректно резолвить относительные ссылки на секции. Например, из шаблона `lg-cfg/sub/_.ctx.md` ссылка `${src}` резолвится в секцию `sub/src`, а не `src`.

Однако при резолве `extends` возникает сложность: к моменту вызова `ExtendsResolver` стек `AddressingContext` уже не отражает контекст конкретной секции — секции уже собраны `SectionCollector` и обрабатываются в цикле.

### Решение: current_dir в ResolvedSection

`ResolvedSection` содержит поле `current_dir`, которое фиксируется в момент резолва секции через `SectionResolver`:

```
SectionResolver._resolve_simple()
    ↓ берёт current_dir из AddressingContext.current_directory
    ↓ сохраняет в ResolvedSection.current_dir
    ↓
ContextResolver._merge_collected_sections()
    ↓ передаёт resolved_section.current_dir в ExtendsResolver
    ↓
ExtendsResolver.resolve_from_cfg(current_dir=...)
    ↓ использует current_dir для резолва локальных extends
```

Это позволяет сохранить информацию о директории в момент, когда `AddressingContext` актуален, и использовать её позже при резолве extends.

### Ключевые классы

- **AddressingContext** (`lg/addressing/context.py`) — управляет стеком директорий при обработке шаблонов
- **SectionResolver** (`lg/addressing/section_resolver.py`) — резолвит секции, сохраняя `current_dir`
- **ResolvedSection** (`lg/addressing/types.py`) — содержит `current_dir` для использования при extends

---

## Система условий (`lg/conditions/`)

### AST условий

Условия представлены как иммутабельное дерево из dataclass-ов:

```python
Condition (abstract)
├── TagCondition         # tag:name
├── TagSetCondition      # TAGSET:set:tag
├── TagOnlyCondition     # TAGONLY:set:tag
├── ScopeCondition       # scope:local | scope:parent
├── TaskCondition        # task
├── ProviderCondition    # provider:base-id
├── GroupCondition       # (condition)
├── NotCondition         # NOT condition
└── BinaryCondition      # left AND|OR right
```

### Разделение ответственности

- `ConditionParser` (`lg/conditions/parser.py`) — парсинг строки в AST
- `ConditionEvaluator` (`lg/conditions/evaluator.py`) — вычисление AST
- `ConditionContext` (`lg/run_context.py`) — контекст с активными тегами/режимами

**Паттерн Visitor**: `ConditionEvaluator` реализует обход AST через `switch` по `ConditionType`, делегируя примитивные проверки в `ConditionContext`.

### Семантика операторов

| Оператор | Описание |
|----------|----------|
| `tag:name` | True если тег активен |
| `TAGSET:set:tag` | Permissive: True если set не активен ИЛИ tag активен |
| `TAGONLY:set:tag` | Restrictive: True только если tag — единственный активный в set |
| `scope:local` | True в локальном скоупе (origin = "self") |
| `scope:parent` | True при рендеринге из родительского скоупа |
| `provider:base-id` | True если `--provider` совпадает после нормализации |
| `task` | True если есть непустой `--task` или `default_task` |

### Нормализация provider-id

Функция `normalize_provider_id()` в `lg/run_context.py` отсекает технический суффикс:
- `.cli` — CLI-инструмент
- `.ext` — IDE-расширение
- `.api` — прямой API

Пример: `com.anthropic.claude.cli` → `com.anthropic.claude`

---

## Интеграция с шаблонным движком

### TemplateContext (`lg/template/context.py`)

Управляет состоянием во время рендеринга шаблона.

**Состояние** (`TemplateState`):
- `active_tags: Set[str]` — активные теги (из CLI + из mode.tags)
- `active_modes: Dict[str, str]` — активные режимы (modeset → mode)
- `mode_options: ModeOptions` — опции из активных режимов (vcs_mode)

**Стек состояний**: при входе в `{% mode %}` состояние сохраняется в стек, при выходе — восстанавливается.

**Валидация**: `{% mode modeset:mode %}` проверяется на существование в `AdaptiveModel` контекста. Несуществующий режим — ошибка `InvalidModeReferenceError`.

### Эффективный task-text

`TemplateContext.get_effective_task_text()` возвращает текст задачи с приоритетами:
1. Явный `--task` (если непустой)
2. `default_task` из активных режимов (объединяются через `\n\n`)
3. `None`

---

## CLI-интерфейс

### Команды list

```bash
# Режимы с фильтрацией по провайдеру
listing-generator list mode-sets --context <ctx> --provider <provider-id>

# Теги
listing-generator list tag-sets --context <ctx>

# Контексты с фильтрацией по провайдеру
listing-generator list contexts [--provider <provider-id>]
```

### Логика фильтрации mode-sets

1. **Контентные наборы** возвращаются полностью (без фильтрации)
2. **Интеграционный набор** фильтруется: режимы без `runs[provider-id]` исключаются
3. Исключение: `clipboard` совместим со всеми режимами

### JSON-схемы

- `lg/adaptive/mode_sets_list.schema.json` — схема ответа list mode-sets
- `lg/adaptive/tag_sets_list.schema.json` — схема ответа list tag-sets

Pydantic-модели генерируются из схем через `datamodel-codegen`.

---

## Мета-секции и Frontmatter

### Мета-секции

Секция **без `filters`** — мета-секция. Она:
- не может рендериться напрямую (`MetaSectionRenderError`)
- используется только для наследования через `extends`
- может включаться через frontmatter `include`

**Типичное применение**: каноничная мета-секция `ai-interaction.sec.yaml` с интеграционными режимами, генерируемая IDE-плагинами.

### Frontmatter в `.ctx.md`

```yaml
---
include:
  - "ai-interaction"
  - "tags/common"
---
```

Секции из `include`:
- добавляются в расчёт режимов/тегов
- **не рендерятся** в финальном выводе
- frontmatter удаляется перед рендерингом (`strip_frontmatter`)

---

## Обработка ошибок

Все ошибки наследуются от `AdaptiveError` (→ `LGUserError`):

| Ошибка | Причина |
|--------|---------|
| `ExtendsCycleError` | Цикл в цепочке extends |
| `MetaSectionRenderError` | Попытка рендера секции без filters |
| `MultipleIntegrationModeSetsError` | >1 интеграционного набора в контексте |
| `NoIntegrationModeSetError` | 0 интеграционных наборов в контексте |
| `ProviderNotSupportedError` | Провайдер не поддерживается контекстом |
| `InvalidModeReferenceError` | {% mode %} ссылается на несуществующий режим |
| `SectionNotFoundInExtendsError` | extends ссылается на несуществующую секцию |

---

## Точки расширения

### Добавление нового условного оператора

1. Добавить класс в `lg/conditions/model.py`
2. Добавить тип в `ConditionType`
3. Расширить `ConditionParser` в `lg/conditions/parser.py`
4. Добавить метод `_evaluate_*` в `ConditionEvaluator`
5. Добавить метод проверки в `ConditionContext`

### Добавление нового поля в Mode

1. Расширить `Mode` в `lg/adaptive/model.py`
2. Обновить `Mode.from_dict()` и `Mode.to_dict()`
3. При необходимости — расширить `ModeOptions` и логику мерджа в `TemplateContext`

---

## Связь с Engine

```python
class Engine:
    def __init__(self, options: RunOptions):
        # Создаём общие сервисы
        self.context_resolver, section_service, addressing = create_context_resolver(root, cache)

    def render_context(self, context_name: str) -> str:
        # 1. Резолвим адаптивную модель
        adaptive_data = self.context_resolver.resolve_for_context(context_name)

        # 2. Создаём TemplateProcessor с моделью
        template_processor = self._create_template_processor(adaptive_data.model)

        # 3. Рендерим
        return template_processor.process_template_file(context_name)
```

Фабрика `create_context_resolver()` инкапсулирует создание всей инфраструктуры (`SectionService`, `AddressingContext`, `ContextResolver`).

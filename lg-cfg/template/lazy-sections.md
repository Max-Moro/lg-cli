# Архитектура ленивой загрузки секций

Документ описывает новую архитектуру загрузки конфигураций секций
в Listing Generator. Заменяет жадную загрузку на ленивую с использованием индекса.

## Проблемы текущей архитектуры

### 1. Дублирование кода кэширования

Два независимых кэша для одних и тех же данных:
- `TemplateContext._config_cache` — используется при разрешении ссылок
- `SectionProcessor._config_cache` — используется при обработке секций

Нарушает DRY и потенциально приводит к двойной загрузке одного конфига.

### 2. Не ленивая загрузка

`load_config()` загружает ВСЕ секции из ВСЕХ файлов `sections.yaml` и `*.sec.yaml`
в scope сразу. Даже если шаблон использует только одну секцию из двадцати,
все двадцать загружаются и парсятся.

### 3. Переусложнённый ConfigBasedResolver

Отдельный класс `ConfigBasedResolver` существует параллельно с `PathResolver`,
создавая архитектурную путаницу: два разных механизма разрешения путей с разными API.

### 4. Неявные правила коллизий

Сложные правила формирования `canonical_id` затрудняют предсказание,
какая секция будет загружена. Нет явной системы приоритетов.

### 5. Нет единого источника истины

Секции загружаются "на лету" в разных местах без единого реестра.

---

## Новая архитектура

### Основные принципы

1. **Индекс**: Лёгкий индекс всех секций без парсинга полных `SectionCfg`
2. **Ленивая загрузка**: Загрузка отдельных секций только при первом обращении
3. **Явные приоритеты**: Чёткие правила разрешения коллизий имён
4. **Единый сервис**: Один `SectionService` как единственный источник истины
5. **Без canonical_id**: Используем кортеж `(file_path, local_name)` как уникальный ключ

### Ключевое решение: отказ от canonical_id

В старой архитектуре `canonical_id` был необходим, потому что:
```python
# Старый подход
all_sections: Dict[str, SectionCfg] = {}  # Нужны уникальные строковые ключи
```

Это приводило к:
- Сложным правилам формирования (`sections.yaml` → без префикса, одна секция в `*.sec.yaml` → короткий id)
- Магическим преобразованиям ("tail дублирование", "a/a" → "a")
- Непредсказуемости для пользователя

**В новой архитектуре:**
```python
# Индекс хранит ВСЕ варианты имён
index.sections = {
    "src": SectionLocation(...),           # из lg-cfg/sections.yaml
    "adapters/src": SectionLocation(...),  # из lg-cfg/adapters/sections.yaml
}

# Уникальный ключ для кэша секций
cache_key = (file_path, local_name)  # ("lg-cfg/sections.yaml", "src")
```

**Преимущества:**
- Простые правила именования (без магии)
- Полные имена в индексе служат для поиска, но не для кэширования
- Физическое расположение `(file_path, local_name)` — истинный уникальный идентификатор
- Коллизии разрешаются явно при построении индекса (приоритеты), а не скрыто в правилах формирования ID

---

## Модель данных

### Унификация резолверов через общий интерфейс

Вместо отдельных механизмов для файлов (`PathResolver`) и секций (`ConfigBasedResolver`),
вводится единый интерфейс для всех типов ресурсов.

#### ResourceResolver (Protocol)

```python
from typing import Protocol

class ResourceResolver(Protocol):
    """Общий интерфейс для разрешения любых ресурсов."""

    def resolve(
        self,
        name: str,
        context: AddressingContext
    ) -> ResolvedResource:
        """
        Разрешить имя ресурса в конкретное расположение.

        Args:
            name: Имя ресурса из шаблона
            context: Контекст адресации (current_dir, scope)

        Returns:
            Разрешённый ресурс
        """
        ...
```

#### Базовые типы результатов

```python
@dataclass
class ResolvedResource:
    """Базовый результат разрешения любого ресурса."""
    scope_dir: Path      # Абсолютный путь к scope
    scope_rel: str       # Относительный путь scope от repo root

@dataclass
class ResolvedFile(ResolvedResource):
    """Результат разрешения файлового ресурса (tpl, ctx, md)."""
    resource_path: Path  # Полный путь к файлу
    resource_rel: str    # Путь относительно lg-cfg/

@dataclass
class ResolvedSection(ResolvedResource):
    """
    Результат разрешения секции.

    ВАЖНО: Заменяет старый SectionRef — содержит всю необходимую информацию
    для обработки секции без повторных обращений к SectionService.
    """
    location: SectionLocation     # Где физически лежит секция
    section_config: SectionCfg    # Уже загруженная конфигурация
    name: str                     # Оригинальное имя из шаблона (для диагностики)
```

#### Конкретные реализации

```python
class FileResolver(ResourceResolver):
    """Резолвер для файловых ресурсов (templates, contexts, markdown)."""

    def __init__(self, repo_root: Path):
        self._parser = PathParser()
        self._resolver = PathResolver(repo_root)

    def resolve(self, name: str, context: AddressingContext) -> ResolvedFile:
        # Использует существующую логику PathParser + PathResolver
        ...

class SectionResolver(ResourceResolver):
    """Резолвер для секций из YAML конфигурации."""

    def __init__(self, section_service: SectionService):
        self._service = section_service

    def resolve(self, name: str, context: AddressingContext) -> ResolvedSection:
        # Делегирует в SectionService
        scope_dir = context.cfg_root.parent
        current_dir = context.current_directory

        # 1. Найти секцию в индексе
        location = self._service.find_section(name, current_dir, scope_dir)

        # 2. Лениво загрузить конфигурацию
        section_config = self._service.load_section(location)

        # 3. Вычислить scope_rel
        try:
            scope_rel = scope_dir.relative_to(context.repo_root).as_posix()
            if scope_rel == ".":
                scope_rel = ""
        except ValueError:
            scope_rel = ""

        # 4. Вернуть полностью разрешённую секцию
        return ResolvedSection(
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            location=location,
            section_config=section_config,
            name=name
        )
```

### SectionLocation

```python
@dataclass(frozen=True)
class SectionLocation:
    """Физическое расположение секции в конфигурационных файлах."""
    file_path: Path      # например, lg-cfg/adapters/sections.yaml
    local_name: str      # например, "src" (имя ключа в YAML)
```

### ScopeIndex

```python
@dataclass
class ScopeIndex:
    """Индекс одного scope (одной директории lg-cfg/)."""

    # Полное имя секции → расположение
    # Ключи уникальны; коллизии разрешены при построении индекса
    sections: Dict[str, SectionLocation]

    # Для инвалидации кэша: путь к файлу → mtime
    file_mtimes: Dict[Path, float]
```

### SectionService

```python
class SectionService:
    """Унифицированный сервис для поиска и загрузки секций.

    Живёт в RunContext, предоставляет единую точку доступа к секциям.
    """

    def __init__(self, root: Path, cache: Cache):
        self._root = root
        self._cache = cache
        # Кэш индексов по scope
        self._indexes: Dict[Path, ScopeIndex] = {}
        # Кэш загруженных секций: (file_path, local_name) → SectionCfg
        self._loaded: Dict[tuple[Path, str], SectionCfg] = {}

    def get_index(self, scope_dir: Path) -> ScopeIndex:
        """Получить или построить индекс для scope."""
        ...

    def find_section(
        self,
        name: str,
        current_dir: str,
        scope_dir: Path
    ) -> SectionLocation:
        """Найти секцию по имени с учётом контекста."""
        ...

    def load_section(self, location: SectionLocation) -> SectionCfg:
        """Лениво загрузить одну секцию по её расположению."""
        ...
```

---

## Правила построения индекса

### Порядок обработки (приоритет)

1. **Сначала**: файлы `sections.yaml` (высший приоритет)
2. **Затем**: файлы `*.sec.yaml` (не перезаписывают существующие записи)

### Правила именования для `sections.yaml`

| Расположение | Имя секции | Полное имя в индексе |
|--------------|------------|---------------------|
| `lg-cfg/sections.yaml` | `src` | `"src"` |
| `lg-cfg/adapters/sections.yaml` | `src` | `"adapters/src"` |
| `lg-cfg/foo/bar/sections.yaml` | `api` | `"foo/bar/api"` |

**Правило**: `{префикс_директории}/{local_name}`, где `префикс_директории` пуст для корня.

### Правила именования для `*.sec.yaml`

**Одна секция в файле** — без префикса имени файла:

| Расположение | Имя секции | Полное имя в индексе |
|--------------|------------|---------------------|
| `lg-cfg/docs.sec.yaml` | `intro` | `"intro"` |
| `lg-cfg/adapters/web.sec.yaml` | `api` | `"adapters/api"` |

**Несколько секций в файле** — с префиксом имени файла:

| Расположение | Имена секций | Полные имена в индексе |
|--------------|--------------|------------------------|
| `lg-cfg/docs.sec.yaml` | `intro`, `api` | `"docs/intro"`, `"docs/api"` |
| `lg-cfg/adapters/web.sec.yaml` | `api`, `models` | `"adapters/web/api"`, `"adapters/web/models"` |

### Разрешение коллизий

Когда два источника дают одинаковое полное имя:
- `sections.yaml` побеждает (обрабатывается первым)
- Коллизия молча игнорируется (без ошибки, без предупреждения)

Пример:
```
lg-cfg/sections.yaml:
  intro: {...}           → "intro" (ПОБЕЖДАЕТ)

lg-cfg/docs.sec.yaml:    # одна секция
  intro: {...}           → "intro" (игнорируется, уже существует)
```

---

## Алгоритм построения индекса

```python
def build_index(cfg_root: Path) -> ScopeIndex:
    sections: Dict[str, SectionLocation] = {}
    file_mtimes: Dict[Path, float] = {}

    # Шаг 1: Обрабатываем sections.yaml (приоритет)
    for sections_file in iter_sections_yaml_files(cfg_root):
        file_mtimes[sections_file] = sections_file.stat().st_mtime
        dir_prefix = get_directory_prefix(cfg_root, sections_file)

        for local_name in read_yaml_top_level_keys(sections_file):
            full_name = f"{dir_prefix}/{local_name}" if dir_prefix else local_name
            sections[full_name] = SectionLocation(sections_file, local_name)

    # Шаг 2: Обрабатываем *.sec.yaml (не перезаписываем)
    for sec_file in iter_sec_yaml_files(cfg_root):
        file_mtimes[sec_file] = sec_file.stat().st_mtime
        dir_prefix = get_directory_prefix(cfg_root, sec_file)
        file_stem = sec_file.stem.removesuffix(".sec")

        local_names = list(read_yaml_top_level_keys(sec_file))

        for local_name in local_names:
            if len(local_names) == 1:
                # Одна секция: без префикса файла
                full_name = f"{dir_prefix}/{local_name}" if dir_prefix else local_name
            else:
                # Несколько секций: с префиксом файла
                prefix = f"{dir_prefix}/{file_stem}" if dir_prefix else file_stem
                full_name = f"{prefix}/{local_name}"

            # Не перезаписываем существующие (sections.yaml побеждает)
            if full_name not in sections:
                sections[full_name] = SectionLocation(sec_file, local_name)

    return ScopeIndex(sections=sections, file_mtimes=file_mtimes)
```

---

## Алгоритм поиска секции

```python
def find_section(
    name: str,
    current_dir: str,
    index: ScopeIndex
) -> SectionLocation:
    """
    Найти секцию по имени с учётом контекста.

    Args:
        name: Ссылка на секцию из шаблона (например, "src", "/src", "adapters/src")
        current_dir: Контекст текущей директории (например, "adapters" при обработке
                     шаблона в lg-cfg/adapters/)
        index: Предварительно построенный индекс scope

    Returns:
        SectionLocation для найденной секции

    Raises:
        SectionNotFoundError: Если секция не найдена
    """
    # Абсолютный путь: пропускаем prefix, ищем напрямую
    if name.startswith('/'):
        key = name.lstrip('/')
        if key in index.sections:
            return index.sections[key]
        raise SectionNotFoundError(name, searched=[key])

    # Относительный путь: сначала пробуем с prefix current_dir
    searched = []

    if current_dir:
        prefixed = f"{current_dir}/{name}"
        searched.append(prefixed)
        if prefixed in index.sections:
            return index.sections[prefixed]

    # Затем пробуем без prefix (глобальный поиск)
    searched.append(name)
    if name in index.sections:
        return index.sections[name]

    raise SectionNotFoundError(name, searched=searched)
```

---

## Инвалидация кэша

### Кэш индекса в .lg-cache

Индекс кэшируется на диске в `.lg-cache/sections/{scope_hash}.index` для быстрого старта
при повторных запусках.

#### Структура кэша на диске

```
.lg-cache/
└── sections/
    ├── root.index          # Индекс для корневого scope
    ├── apps_web.index      # Индекс для apps/web scope
    └── libs_core.index     # Индекс для libs/core scope
```

#### Формат кэша

```python
# Сериализация в JSON для читаемости и простоты
{
    "version": "1.0",               # Версия формата кэша
    "scope_dir": "/path/to/scope",  # Абсолютный путь к scope
    "built_at": 1234567890.123,     # Timestamp построения
    "sections": {
        "src": {
            "file_path": "lg-cfg/sections.yaml",
            "local_name": "src"
        },
        "adapters/src": {
            "file_path": "lg-cfg/adapters/sections.yaml",
            "local_name": "src"
        }
    },
    "file_mtimes": {
        "lg-cfg/sections.yaml": 1234567890.123,
        "lg-cfg/adapters/sections.yaml": 1234567891.456
    }
}
```

#### Логика работы с кэшем

```python
class SectionService:
    def get_index(self, scope_dir: Path) -> ScopeIndex:
        # 1. Проверяем memory cache
        if scope_dir in self._indexes:
            return self._indexes[scope_dir]

        # 2. Пробуем загрузить из .lg-cache
        cached = self._load_index_from_cache(scope_dir)
        if cached and self._is_index_valid(cached, scope_dir):
            self._indexes[scope_dir] = cached
            return cached

        # 3. Строим новый индекс
        index = self._build_index(scope_dir)
        self._save_index_to_cache(scope_dir, index)
        self._indexes[scope_dir] = index
        return index

    def _is_index_valid(self, cached_index: ScopeIndex, cfg_root: Path) -> bool:
        """Проверка актуальности кэша по mtime файлов."""
        # Проверяем, изменился ли какой-либо известный файл
        for file_path, cached_mtime in cached_index.file_mtimes.items():
            if not file_path.exists():
                return False  # Файл удалён
            current_mtime = file_path.stat().st_mtime
            if abs(current_mtime - cached_mtime) > 0.001:  # Учёт точности float
                return False  # Файл изменён

        # Проверяем, появились ли новые файлы
        current_files = set(iter_all_config_files(cfg_root))
        cached_files = set(cached_index.file_mtimes.keys())
        if current_files != cached_files:
            return False  # Файлы добавлены или удалены

        return True

    def _load_index_from_cache(self, scope_dir: Path) -> Optional[ScopeIndex]:
        """Загрузка индекса из .lg-cache."""
        cache_key = self._get_cache_key(scope_dir)
        cache_file = self._cache.root / "sections" / f"{cache_key}.index"

        if not cache_file.exists():
            return None

        try:
            import json
            data = json.loads(cache_file.read_text(encoding="utf-8"))

            # Проверка версии формата
            if data.get("version") != "1.0":
                return None

            # Десериализация
            sections = {
                name: SectionLocation(
                    file_path=Path(loc["file_path"]),
                    local_name=loc["local_name"]
                )
                for name, loc in data["sections"].items()
            }

            file_mtimes = {
                Path(fp): mtime
                for fp, mtime in data["file_mtimes"].items()
            }

            return ScopeIndex(sections=sections, file_mtimes=file_mtimes)
        except Exception:
            # Некорректный кэш — игнорируем
            return None

    def _save_index_to_cache(self, scope_dir: Path, index: ScopeIndex) -> None:
        """Сохранение индекса в .lg-cache."""
        cache_key = self._get_cache_key(scope_dir)
        cache_file = self._cache.root / "sections" / f"{cache_key}.index"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        import json
        import time

        data = {
            "version": "1.0",
            "scope_dir": str(scope_dir),
            "built_at": time.time(),
            "sections": {
                name: {
                    "file_path": str(loc.file_path),
                    "local_name": loc.local_name
                }
                for name, loc in index.sections.items()
            },
            "file_mtimes": {
                str(fp): mtime
                for fp, mtime in index.file_mtimes.items()
            }
        }

        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _get_cache_key(self, scope_dir: Path) -> str:
        """Генерация ключа кэша для scope."""
        # Используем относительный путь от repo root
        try:
            rel = scope_dir.relative_to(self._root)
            if rel == Path("."):
                return "root"
            return str(rel).replace("/", "_").replace("\\", "_")
        except ValueError:
            # Scope вне репозитория — хеш абсолютного пути
            import hashlib
            return hashlib.sha256(str(scope_dir).encode()).hexdigest()[:16]
```

#### Преимущества кэширования на диске

1. **Быстрый старт**: Не нужно сканировать и парсить YAML при каждом запуске
2. **Автоматическая инвалидация**: По mtime файлов — пользователь не думает о кэше
3. **Прозрачность**: JSON формат позволяет просматривать содержимое кэша
4. **Безопасность**: Некорректный кэш просто игнорируется, всегда можно пересоздать

### Кэш секций

Загруженные объекты `SectionCfg` кэшируются в памяти по ключу `(file_path, local_name)`.
Кэш инвалидируется при перестроении индекса (изменился mtime файла).

---

## Интеграция с существующим кодом

### RunContext

```python
@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    gitignore: Optional[GitIgnoreService]
    tokenizer: TokenService
    adaptive_loader: AdaptiveConfigLoader
    mode_options: ModeOptions
    active_tags: Set[str]
    section_service: SectionService  # НОВОЕ
```

### TemplateContext

Удалить `_config_cache` и `config_resolver`. Использовать `run_ctx.section_service`.

```python
class TemplateContext:
    def __init__(self, run_ctx: RunContext):
        self.run_ctx = run_ctx
        # Удалить: self._config_cache
        # Удалить: self.config_resolver
```

### SectionProcessor

Удалить `_config_cache`. Принимать `ResolvedSection` вместо `SectionRef`.

```python
class SectionProcessor:
    def __init__(self, run_ctx: RunContext, stats_collector: StatsCollector):
        self.run_ctx = run_ctx
        # Удалить: self._config_cache
        # Удалить: self._get_config()

    def process_section(
        self,
        resolved: ResolvedSection,
        template_ctx: TemplateContext
    ) -> RenderedSection:
        """
        Обработать разрешённую секцию.

        Args:
            resolved: Полностью разрешённая секция (из резолвера)
            template_ctx: Контекст шаблонизатора

        Returns:
            Отрендеренная секция
        """
        # НИКАКИХ вызовов section_service!
        # Всё уже есть в resolved

        manifest = build_section_manifest(
            resolved=resolved,
            section_config=resolved.section_config,  # уже загружена
            template_ctx=template_ctx,
            root=self.run_ctx.root,
            vcs=self.run_ctx.vcs,
            gitignore_service=self.run_ctx.gitignore,
            vcs_mode=template_ctx.current_state.mode_options.vcs_mode,
            target_branch=self.run_ctx.options.target_branch
        )

        plan = build_section_plan(manifest, template_ctx)
        processed_files = process_files(plan, template_ctx)

        # Регистрация в статистике
        for pf in processed_files:
            self.stats_collector.register_processed_file(file=pf, resolved=resolved)

        rendered = render_section(plan, processed_files)
        self.stats_collector.register_section_rendered(rendered)

        return rendered
```

### Обработчик секций в процессоре

Обработчик должен вызывать `SectionProcessor.process_section()` с `ResolvedSection`.

```python
# В CommonPlaceholdersPlugin.register_processors()
def process_section_node(processing_context: ProcessingContext) -> str:
    """Обрабатывает SectionNode через typed handlers."""
    node = processing_context.get_node()
    if not isinstance(node, SectionNode):
        raise RuntimeError(f"Expected SectionNode, got {type(node)}")

    # node.resolved_section заполнен резолвером, содержит всё необходимое
    if node.resolved_section is None:
        raise RuntimeError(f"Section '{node.name}' not resolved")

    # Вызываем обработку через handler
    # Handler делегирует в SectionProcessor.process_section(resolved, template_ctx)
    return self.handlers.process_section(node.resolved_section)
```

---

## Интеграция с системой addressing

### Использование резолверов в плагинах

Плагины (например, `CommonPlaceholdersPlugin`) будут использовать резолверы через
унифицированный интерфейс, не зная о деталях реализации.

```python
# В CommonPlaceholdersResolver
class CommonPlaceholdersResolver:
    def __init__(
        self,
        handlers: TemplateProcessorHandlers,
        registry: TemplateRegistryProtocol,
        template_ctx: TemplateContext,
    ):
        self.template_ctx = template_ctx
        # Получаем резолверы из контекста
        self.section_resolver = template_ctx.get_section_resolver()
        self.file_resolver = template_ctx.get_file_resolver()

    def _resolve_section_node(self, node: SectionNode) -> SectionNode:
        # Используем SectionResolver через единый интерфейс
        resolved = self.section_resolver.resolve(
            node.name,
            self.template_ctx.addressing
        )

        # resolved это ResolvedSection — содержит ВСЁ необходимое:
        # - location для идентификации
        # - section_config уже загружена
        # - scope_dir, scope_rel для контекста

        return SectionNode(node.name, resolved_section=resolved)

    def _resolve_include_node(self, node: IncludeNode) -> IncludeNode:
        # Используем FileResolver для tpl/ctx
        config = CONTEXT_CONFIG if node.kind == "ctx" else TEMPLATE_CONFIG
        resolved = self.file_resolver.resolve(
            node.name,
            config,
            self.template_ctx.addressing
        )

        # Загружаем и парсим шаблон
        template_text = resolved.resource_path.read_text(encoding="utf-8")
        ast = self.handlers.parse_template(template_text)

        return IncludeNode(
            kind=node.kind,
            name=node.name,
            origin=resolved.scope_rel or "self",
            children=ast,
            resolved_path=resolved.resource_path
        )
```

### Обновление TemplateContext

```python
class TemplateContext:
    def __init__(self, run_ctx: RunContext):
        self.run_ctx = run_ctx

        # Удалить: self._config_cache
        # Удалить: self.config_resolver

        # Создать резолверы
        self._section_resolver = SectionResolver(run_ctx.section_service)
        self._file_resolver = FileResolver(run_ctx.root)

    def get_section_resolver(self) -> SectionResolver:
        """Получить резолвер секций."""
        return self._section_resolver

    def get_file_resolver(self) -> FileResolver:
        """Получить резолвер файлов."""
        return self._file_resolver
```

---

## Файлы для изменения

### Зоны ответственности нового пакета `lg/section/*`

**Отвечает за:**
- Построение индекса секций из YAML файлов
- Ленивую загрузку конфигураций секций (`SectionCfg`)
- Кэширование (memory + disk)
- Публичное API для получения списка секций

**НЕ отвечает за:**
- Обработку секций (это `section_processor.py` — ядро пайплайна)
- Построение манифестов (это `filtering/manifest.py`)
- Обработку файлов в секциях (это `adapters/*`, `rendering/*`)

### Новые файлы

1. **`lg/section/__init__.py`**
   - Публичное API: `SectionService`, `SectionLocation`, `ScopeIndex`
   - Реэкспорт модели: `SectionCfg`, `AdapterConfig`, `TargetRule`

2. **`lg/section/model.py`** (перенос из `lg/config/model.py`)
   - `SectionCfg` — модель секции
   - `AdapterConfig` — конфигурация адаптеров
   - `ConditionalAdapterOptions` — условные опции адаптеров
   - `TargetRule` — целевые правила
   - `EmptyPolicy` — политика пустых файлов

3. **`lg/section/service.py`**
   - `SectionService` — основной сервис
   - Логика кэширования (memory + disk)
   - Методы `get_index()`, `find_section()`, `load_section()`
   - Методы `list_sections()`, `list_sections_peek()` (перенос из `lg/config/load.py`)

4. **`lg/section/index.py`**
   - Функция `build_index(cfg_root: Path) -> ScopeIndex`
   - `_collect_sections_from_sections_yaml()` (перенос из `lg/config/load.py`)
   - `_collect_sections_from_fragments()` (перенос из `lg/config/load.py`)

5. **`lg/section/paths.py`** (перенос из `lg/config/paths.py`)
   - `sections_path()` — путь к главному файлу секций
   - `iter_sections_yaml_files()` — все sections.yaml файлы
   - `iter_section_fragments()` — все *.sec.yaml файлы
   - `canonical_fragment_prefix()` — префикс для фрагмента
   - `sections_yaml_prefix()` — префикс для sections.yaml

6. **`lg/template/addressing/types.py`** (обновить)
   - Добавить `ResolvedResource`, `ResolvedFile`, `ResolvedSection`
   - Добавить Protocol `ResourceResolver`

7. **`lg/template/addressing/resolvers.py`** (новый)
   - `FileResolver` — обёртка над PathParser + PathResolver
   - `SectionResolver` — использует SectionService

### Файлы для изменения

8. **`lg/run_context.py`**
   - Добавить поле `section_service: SectionService`

9. **`lg/engine.py`**
   - Создать экземпляр `SectionService` при инициализации
   - Передать в `RunContext`

10. **`lg/template/context.py`**
    - Удалить `_config_cache` и `config_resolver`
    - Добавить `_section_resolver` и `_file_resolver`
    - Добавить методы `get_section_resolver()` и `get_file_resolver()`

11. **`lg/section_processor.py`**
    - Удалить `_config_cache` и `_get_config()`
    - Изменить сигнатуру: `process_section(resolved: ResolvedSection, ...)` вместо `process_section(section_ref: SectionRef, ...)`
    - Убрать все обращения к `section_service` внутри методов — вся информация уже в `resolved`

12. **`lg/template/common_placeholders/resolver.py`**
    - Заменить вызовы `config_resolver` на `section_resolver`
    - Использовать `file_resolver` для tpl/ctx
    - Обновить `_resolve_section_node()` — возвращать `SectionNode` с `resolved_section`

13. **`lg/template/handlers.py`**
    - Обновить `TemplateProcessorHandlers` protocol:
    - Изменить сигнатуру: `process_section(resolved: ResolvedSection)` вместо `process_section_ref(section_ref: SectionRef)`

14. **`lg/template/processor.py`**
    - Обновить реализацию handlers в `ProcessorHandlers` inner class
    - Метод `process_section()` теперь принимает `ResolvedSection` и делегирует в `SectionProcessor`

15. **`lg/config/model.py`**
    - Удалить `SectionCfg`, `AdapterConfig`, `ConditionalAdapterOptions`, `TargetRule`, `EmptyPolicy`
    - Все перенесены в `lg/section/model.py`
    - Класс `Config` может остаться пустым или быть удалён полностью

16. **`lg/config/load.py`**
    - Удалить `_collect_sections_from_sections_yaml()`, `_collect_sections_from_fragments()`
    - Удалить `list_sections()`, `list_sections_peek()`
    - Функция `load_config()` либо удаляется, либо упрощается (если останется логика для НЕ-секционных конфигов)

17. **`lg/config/paths.py`**
    - Удалить `sections_path()`, `iter_sections_yaml_files()`, `iter_section_fragments()`
    - Удалить `canonical_fragment_prefix()`, `sections_yaml_prefix()`
    - Оставить только общие константы и функции: `cfg_root()`, `CFG_DIR`, `models_path()`, `modes_path()`, `tags_path()`

18. **`lg/config/__init__.py`**
    - Обновить экспорты: убрать `list_sections`, `list_sections_peek`, `SectionCfg`
    - Добавить реэкспорт из `lg/section`: `from lg.section import SectionCfg, list_sections` (для обратной совместимости импортов)

19. **`lg/cli.py`**
    - Обновить импорт: `from lg.section import list_sections` вместо `from .config import list_sections`

20. **`lg/diag/diagnostics.py`**
    - Обновить импорт: `from lg.section import list_sections_peek` вместо `from lg.config import list_sections_peek`

### Файлы для удаления

21. **`lg/template/addressing/config_based_resolver.py`**
    - Полностью удалить, заменён на `SectionResolver`

---

## Заметки по миграции

### Обратная совместимость

Новые правила именования идентичны текущим правилам `canonical_id`:
- Все существующие ссылки в шаблонах продолжат работать
- Изменения в пользовательских конфигурациях не требуются

### Стратегия тестирования

1. Проверить, что построение индекса даёт те же результаты, что текущий `load_config()`
2. Проверить, что алгоритм поиска находит те же секции, что текущий резолвер
3. Проверить корректность инвалидации кэша
4. Тестирование производительности: сравнить потребление памяти и время старта

---

## Легаси и мёртвый код для удаления

После завершения рефакторинга следующий код становится мёртвым и должен быть удалён:

### Файлы для полного удаления

| Файл | Причина |
|------|---------|
| `lg/template/addressing/config_based_resolver.py` | Заменён на `SectionService.find_section()` |

### Код для удаления в существующих файлах

#### `lg/template/context.py` (TemplateContext)

```python
# Удалить поле
self._config_cache: Dict[Path, 'Config'] = {}

# Удалить поле
self.config_resolver = ConfigBasedResolver(...)

# Удалить метод
def get_config(self, scope_dir: Path) -> Config:
    ...
```

#### `lg/section_processor.py` (SectionProcessor)

```python
# Удалить поле
self._config_cache: Dict[Path, Config] = {}

# Удалить метод
def _get_config(self, scope_dir: Path) -> Config:
    ...
```

#### `lg/config/load.py`

```python
# ПЕРЕНОСИМ в lg/section/index.py:
def _collect_sections_from_sections_yaml(root: Path) -> Dict[str, SectionCfg]:
    ...

def _collect_sections_from_fragments(root: Path) -> Dict[str, SectionCfg]:
    ...

# ПЕРЕНОСИМ в lg/section/service.py:
def list_sections(root: Path) -> List[str]:
    ...

def list_sections_peek(root: Path) -> List[str]:
    ...

# Функция load_config() УДАЛЯЕТСЯ или упрощается:
# - Если Config класс остаётся для других целей, может остаться заглушка
# - Иначе полностью удаляется
def load_config(root: Path) -> Config:
    ...
```

#### `lg/config/model.py`

```python
# ПЕРЕНОСИМ в lg/section/model.py:
class SectionCfg:
    ...

class AdapterConfig:
    ...

class ConditionalAdapterOptions:
    ...

class TargetRule:
    ...

EmptyPolicy = Literal["inherit", "include", "exclude"]

# Класс Config остаётся пустым или удаляется:
@dataclass
class Config:
    sections: Dict[str, SectionCfg]  # ← УДАЛИТЬ это поле
```

#### `lg/config/paths.py`

```python
# ПЕРЕНОСИМ в lg/section/paths.py:
def sections_path(root: Path) -> Path:
    ...

def iter_sections_yaml_files(root: Path) -> List[Path]:
    ...

def iter_section_fragments(root: Path) -> List[Path]:
    ...

def canonical_fragment_prefix(root: Path, frag: Path) -> str:
    ...

def sections_yaml_prefix(root: Path, sections_file: Path) -> str:
    ...

# ОСТАЁТСЯ в lg/config/paths.py (общие константы):
# - CFG_DIR, SECTIONS_FILE, MODELS_FILE, MODES_FILE, TAGS_FILE
# - cfg_root(), models_path(), modes_path(), tags_path()
```

### Импорты для удаления

После удаления вышеуказанного кода проверить и удалить неиспользуемые импорты:

- `from .config import load_config` — в файлах, где использовался только для секций
- `from .addressing.config_based_resolver import ConfigBasedResolver` — в `context.py`
- `from ..config import Config, load_config` — в `section_processor.py`

### Типы для ревизии

#### `lg/types.py`

```python
# SectionRef больше не нужен — заменён на ResolvedSection
@dataclass(frozen=True)
class SectionRef:  # ← УДАЛИТЬ
    name: str
    scope_rel: str
    scope_dir: Path
```

**Замена:** Везде, где использовался `SectionRef`, теперь используется `ResolvedSection` из `lg/template/addressing/types.py`.

#### `lg/template/common_placeholders/nodes.py`

```python
@dataclass(frozen=True)
class SectionNode(TemplateNode):
    """Section placeholder ${section}."""
    name: str
    # Было: resolved_ref: Optional[SectionRef] = None
    # Стало:
    resolved_section: Optional[ResolvedSection] = None
```

#### `lg/config/model.py`

```python
# Класс Config может упроститься, если sections больше не хранятся целиком:
@dataclass
class Config:
    sections: Dict[str, SectionCfg]  # ← возможно станет не нужен
```

Решить: оставить `Config` для других целей или удалить полностью.

### Тесты для обновления/удаления

После рефакторинга проверить тесты:

1. Тесты `load_config()` — адаптировать под новую архитектуру
2. Тесты `ConfigBasedResolver` — удалить, заменить тестами `SectionService`
3. Тесты кэширования в `TemplateContext` и `SectionProcessor` — удалить дублирующиеся

### Чеклист финальной очистки

**Удаление легаси:**
- [ ] Удалён `config_based_resolver.py`
- [ ] Удалены `_config_cache` из `TemplateContext` и `SectionProcessor`
- [ ] Удалены методы `get_config()` и `_get_config()`
- [ ] Удалён тип `SectionRef` из `lg/types.py`
- [ ] Заменены все использования `SectionRef` на `ResolvedSection`
- [ ] Обновлён `SectionNode`: `resolved_ref` → `resolved_section`

**Перенос в lg/section/*:**
- [ ] Перенесён `SectionCfg` и связанные классы из `lg/config/model.py` → `lg/section/model.py`
- [ ] Перенесены функции обхода файлов из `lg/config/paths.py` → `lg/section/paths.py`
- [ ] Перенесены функции сбора секций из `lg/config/load.py` → `lg/section/index.py`
- [ ] Перенесены `list_sections()`, `list_sections_peek()` → `lg/section/service.py`
- [ ] Очищен `lg/config/model.py` — удалено секционное содержимое
- [ ] Очищен `lg/config/load.py` — удалены функции сбора секций
- [ ] Очищен `lg/config/paths.py` — удалены секционные функции

**Обновление импортов:**
- [ ] Обновлён `lg/config/__init__.py` — реэкспорт из `lg/section`
- [ ] Обновлён `lg/cli.py` — импорт `list_sections` из `lg/section`
- [ ] Обновлён `lg/diag/diagnostics.py` — импорт `list_sections_peek` из `lg/section`
- [ ] Обновлены все импорты `SectionCfg` на `from lg.section import SectionCfg`
- [ ] Очищены неиспользуемые импорты

**Проверки:**
- [ ] Обновлены/удалены соответствующие тесты
- [ ] Проверено отсутствие ссылок на удалённый код (grep по кодовой базе)
- [ ] Запущен Qodana для поиска мёртвого кода
- [ ] Все тесты проходят после рефакторинга

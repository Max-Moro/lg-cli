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

---

## Модель данных

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

### Кэш индекса

Индекс кэшируется в `.lg-cache` с автоматической инвалидацией по mtime файлов.

```python
def is_index_valid(cached_index: ScopeIndex, cfg_root: Path) -> bool:
    # Проверяем, изменился ли какой-либо известный файл
    for file_path, cached_mtime in cached_index.file_mtimes.items():
        if not file_path.exists():
            return False  # Файл удалён
        if file_path.stat().st_mtime != cached_mtime:
            return False  # Файл изменён

    # Проверяем, появились ли новые файлы
    current_files = set(iter_all_config_files(cfg_root))
    cached_files = set(cached_index.file_mtimes.keys())
    if current_files != cached_files:
        return False  # Файлы добавлены или удалены

    return True
```

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

Удалить `_config_cache`. Использовать `run_ctx.section_service`.

```python
class SectionProcessor:
    def __init__(self, run_ctx: RunContext, stats_collector: StatsCollector):
        self.run_ctx = run_ctx
        # Удалить: self._config_cache

    def _build_manifest(self, section_ref: SectionRef, template_ctx):
        # Используем сервис вместо прямой загрузки конфига
        location = self.run_ctx.section_service.find_section(
            section_ref.name,
            template_ctx.addressing.current_directory,
            section_ref.scope_dir
        )
        section_config = self.run_ctx.section_service.load_section(location)
        ...
```

### CommonPlaceholdersResolver

Заменить `ConfigBasedResolver` на прямые вызовы `SectionService`.

```python
def _resolve_section_node(self, node: SectionNode) -> SectionNode:
    scope_dir = self.template_ctx.addressing.cfg_root.parent
    current_dir = self.template_ctx.addressing.current_directory

    location = self.template_ctx.run_ctx.section_service.find_section(
        node.name,
        current_dir,
        scope_dir
    )

    section_ref = SectionRef(
        name=...,  # формируется из location
        scope_rel=...,
        scope_dir=scope_dir
    )

    return SectionNode(node.name, section_ref)
```

---

## Файлы для изменения

1. **Новый файл**: `lg/section/service.py` — `SectionService`, `ScopeIndex`, `SectionLocation`
2. **Новый файл**: `lg/section/index.py` — логика построения индекса
3. **Изменить**: `lg/run_context.py` — добавить поле `section_service`
4. **Изменить**: `lg/engine.py` — создать экземпляр `SectionService`
5. **Изменить**: `lg/template/context.py` — удалить `_config_cache`, `config_resolver`
6. **Изменить**: `lg/section_processor.py` — использовать `section_service`
7. **Изменить**: `lg/template/common_placeholders/resolver.py` — использовать `section_service`
8. **Удалить**: `lg/template/addressing/config_based_resolver.py` — больше не нужен

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
# Удалить или переработать (логика переезжает в SectionService):
def _collect_sections_from_sections_yaml(root: Path) -> Dict[str, SectionCfg]:
    ...

def _collect_sections_from_fragments(root: Path) -> Dict[str, SectionCfg]:
    ...

# Функция load_config() может остаться для загрузки НЕ-секционных частей конфига,
# но логика загрузки секций должна быть удалена или делегирована в SectionService
```

### Импорты для удаления

После удаления вышеуказанного кода проверить и удалить неиспользуемые импорты:

- `from .config import load_config` — в файлах, где использовался только для секций
- `from .addressing.config_based_resolver import ConfigBasedResolver` — в `context.py`
- `from ..config import Config, load_config` — в `section_processor.py`

### Типы для ревизии

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

- [ ] Удалён `config_based_resolver.py`
- [ ] Удалены `_config_cache` из `TemplateContext` и `SectionProcessor`
- [ ] Удалены методы `get_config()` и `_get_config()`
- [ ] Очищены неиспользуемые импорты
- [ ] Обновлены/удалены соответствующие тесты
- [ ] Проверено отсутствие ссылок на удалённый код (grep по кодовой базе)
- [ ] Запущен Qodana для поиска мёртвого кода

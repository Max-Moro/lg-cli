# Рекомендации по разработке в данном проекте

В данном проекте ведется разработка плагина для **IntelliJ Platform**. Это вполне традиционный по структуре проект для этих целей.

## Архитектура

**Паттерн:** Слоистая сервис-ориентированная архитектура с реактивным управлением состоянием UI.

### Слои

**CLI Integration** (`lg/intellij/cli/`)
- `CliExecutor` — асинхронный запуск внешней CLI `lg` с timeout/stdin
- `CliResolver` — поиск исполняемого файла (venv → system Python → pipx)
- `CliResult` — sealed class для type-safe обработки результатов

**Services** (`lg/intellij/services/`)
- **Generation**: `LgGenerationService` (рендеринг), `LgStatsService` (токены)
- **Catalog**: `LgCatalogService` (секции/контексты/режимы/теги), `TokenizerCatalogService` (библиотеки/энкодеры)
- **State**:
    - `LgSettingsService` — app-level (путь к CLI, AI провайдер)
    - `LgPanelStateService` — project-level UI (выбранные section/template, режимы, теги, task text) с `StateFlow`
    - `LgWorkspaceStateService` — UI layout (режимы отображения, позиции сплиттеров)
- **Diagnostics/Git**: `LgDiagnosticsService`, `LgGitService`, `LgErrorReportingService`

**Actions** (`lg/intellij/actions/`)
- Базовый `LgGenerateAction` параметризован `GenerationTarget` (SECTION/CONTEXT)
- Actions → background tasks → CLI execution → parse JSON → open in editor

**UI** (`lg/intellij/ui/`)
- Tool Window: вертикальный split (Control Panel + Included Files)
- Panels: `LgControlPanel`, `LgModeSetsPanel`, `LgIncludedFilesPanel`
- Кастомные компоненты: `LgTaskTextField`, `LgEncoderCompletionField`, `LgGroupedTable`

### Управление состоянием

- Реактивное: `StateFlow` для синхронизации task text между панелью и диалогами
- Персистентное: `BaseState` properties → `workspace.xml` (panel state) / `lg-settings.xml` (app settings)
- Эффективные значения: Panel state с fallback на application defaults

## Важные особенности

**Kotlin Coroutines**
- Все CLI операции — suspend functions
- UI updates через `coroutineScope.launch`

**Запрет на object**
- НЕ используй Kotlin `object` для классов в `plugin.xml` (проблемы с DI)
- Только `class` для Services, Actions, etc.

**VFS Listeners**
- `LgConfigFileListener` — авто-перезагрузка каталогов при изменении `lg-cfg/`

**AI Integration**
- Опциональная интеграция через плагины: JetBrains AI, GitHub Copilot, Junie
- Установка в песочницу вручную, сохраняется между запусками

## Стек

- **Platform**: IntelliJ IDEA Community 2025.2.3
- **JVM**: 21 (toolchain)
- **Gradle**: 9.0.0
- **Kotlin**: см. `libs.versions.toml`
- **IntelliJ Platform Gradle Plugin**: 2.x

## Тестирование

Проект не имеет автоматических тестов. Тестирование делается пользователем через запуск IntelliJ IDEA (Development Instance) с установленным плагином.

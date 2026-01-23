# ТЗ: IntelliJ Plugin — новая система режимов и тегов

Дата: 2026-01-23

## 1. Цели

Обновить IntelliJ Plugin для поддержки новой системы режимов/тегов:
- контекстные mode‑sets/tag‑sets;
- разделение mode‑sets на интеграционные и контентные;
- выбор AI‑провайдера в Control Panel (не в Settings);
- использование `runs` для запуска провайдеров;
- хранение состояния per (context, provider) и per context.

---

## 2. Область работ

### Включено
- UI: провайдерный селектор в Tool Window (Control Panel);
- запрос mode‑sets/tag‑sets с учётом контекста/провайдера;
- хранение состояния по контексту/провайдеру;
- обновление интеграции с AI‑провайдерами через `runs`.

### Не включено
- миграция legacy state вне `.idea/workspace.xml`;
- изменения CLI (делается в отдельном ТЗ).

---

## 3. Новая модель данных (клиент)

### 3.1. Состояние панели
Изменить `LgPanelStateService.State`:

```kotlin
var providerId: String
var modesByContextProvider: MutableMap<String, MutableMap<String, MutableMap<String, String>>>
var tagsByContext: MutableMap<String, MutableMap<String, MutableSet<String>>>
```

- `modesByContextProvider[ctx][provider][modeset] = modeId`.
- `tagsByContext[ctx][tagset] = {tagId}`.

### 3.2. Модели list‑ответов
Обновить Kotlin‑модели mode‑sets:
- поле `integration: Boolean` у ModeSet;
- поле `runs: Map<String, String>?` у Mode.

---

## 4. Изменения UI (Tool Window)

### 4.1. Новый селектор провайдера
Добавить комбобокс выбора provider в Control Panel (рядом с контекстами или в Adaptive Settings).

Источник данных: `AiIntegrationService.detectAvailableProviders()` + provider name.

### 4.2. Перенос выбора провайдера из Settings
`LgSettingsService.state.aiProvider` остаётся **fallback** (начальное значение).
Реальный выбор хранится в `LgPanelStateService`.

### 4.3. Обновление списков
При изменении контекста или провайдера:
- перезапрашивать mode‑sets (context + provider)
- перезапрашивать tag‑sets (context)

---

## 4.4. Генерация/обновление `lg-cfg/ai-interaction.sec.yaml`

### Кнопка в туллбаре
Добавить отдельную action‑кнопку в туллбар Tool Window:
- Название: например **“Update AI Modes Template”**
- Действие: генерация/обновление `lg-cfg/ai-interaction.sec.yaml`.

### Требования к генерации
Перед генерацией плагин должен опросить **все зарегистрированные AI‑провайдеры**:
- какие `runs` они поддерживают;
- к каким пользовательским режимам (ask/agent/plan/…) их разумно применять.

### Merge‑логика
- Обновление **не перетирает** неизвестные/чужие ключи.
- Плагин изменяет только те части YAML, которые может объяснить (свои `runs`).
- Если файл уже существует, нужно **добавлять/обновлять** поддерживаемые `runs`, не удаляя остальные.

### Совместимость
Файл должен быть совместим между VS Code и IntelliJ плагинами:
- оба плагина могут обновлять один и тот же `ai-interaction.sec.yaml`;
- если провайдер незнаком плагину, его данные сохраняются как есть.

---

## 5. Интеграция с CLI

### 5.1. Новые вызовы
Обновить `LgCatalogService` и `CliExecutor` вызовы:

```
list mode-sets --context <ctx> --provider <provider>
list tag-sets  --context <ctx>
```

### 5.2. Генерация render/report
`LgGenerationService` должен использовать:
- modes: `modesByContextProvider[currentCtx][currentProvider]`
- tags: `tagsByContext[currentCtx]`

---

## 6. Работа с `runs` и режимами

### 6.1. Правило единственного интеграционного набора
UI ожидает ровно один интеграционный mode‑set. Если его нет → ошибка пользователю.

### 6.2. Исполнение `runs`

#### Extension‑провайдеры (JetBrains AI, Copilot, Junie)
- `runs` трактуется как команда/инструкция для конкретного провайдера.
- Реализовать интерпретацию в конкретных provider‑классах.

#### CLI‑провайдеры (Claude/Codex)
- `runs` — строка флагов.
- Провайдеры парсят строку и устанавливают параметры запуска.

### 6.3. Удаление `AiInteractionMode`
- Удалить Enum `AiInteractionMode` и всю логику его использования.
- Провайдеры должны работать через `runs`.

---

## 7. Изменения в коде

### 7.1. LgPanelStateService
- новая структура state;
- методы `getCurrentModes(ctx, provider)` и `getCurrentTags(ctx)`;
- `actualizeState()` под новый формат.

### 7.2. LgCatalogService
- новый API list‑команд;
- актуализация state после загрузки каталогов.

### 7.3. AiIntegrationService
- метод `sendTo(providerId, content, runs)`;
- извлечение `runs` из выбранного интеграционного режима.

### 7.4. Providers
- переписать provider‑классы под `runs`.
- CLAUDE/CODEX: парсинг строковых флагов.
- JetBrains AI / Copilot / Junie: интерпретация строки `runs` по логике конкретного инструмента.

---

## 8. Безопасность

- При обнаружении нестандартных/неизвестных `runs` показывать предупреждение.
- Подтверждение пользователя перед первым запуском таких `runs` в проекте.

---

## 9. Тесты/проверки

Минимум:
1) Смена context → обновление mode‑sets/tag‑sets.
2) Смена provider → обновление mode‑sets.
3) Отправка в AI использует `runs`.
4) Ошибка при отсутствии интеграционного набора.

---

## 10. Рефакторинги

- удалить `AiInteractionMode` и связанный маппинг;
- выделить общий парсер `runs` для CLI‑провайдеров.

---

## 11. Выходные артефакты

- Обновлённый UI с селектором провайдера.
- Новое хранение состояния per (context, provider).
- Обновлённые интеграции с AI через `runs`.
- Поддержка новых list‑команд CLI.

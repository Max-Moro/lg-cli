# ТЗ: VS Code Extension — новая система режимов и тегов

Дата: 2026-01-23

## 1. Цели

Обновить VS Code Extension для поддержки новой системы режимов/тегов:
- контекстные mode‑sets/tag‑sets;
- разделение mode‑sets на интеграционные и контентные;
- выбор AI‑провайдера в Control Panel (не в Settings);
- использование `runs` для запуска провайдеров;
- хранение состояния per (context, provider) и per context.

---

## 2. Область работ

### Включено
- UI: провайдерный селектор в Control Panel;
- запрос mode‑sets/tag‑sets с учётом контекста/провайдера;
- хранение состояния по контексту/провайдеру;
- обновление интеграции с AI‑провайдерами через `runs`.

### Не включено
- миграция legacy state за пределами текущего workspace state;
- изменение CLI (делается в отдельном ТЗ).

---

## 3. Новая модель данных (клиент)

### 3.1. Состояние Control Panel
Изменить модель состояния:

```ts
interface ControlPanelState {
  // ... как сейчас
  providerId: string; // выбранный провайдер (из Control Panel)

  // режимы по (context, provider)
  modesByContextProvider: Record<string, Record<string, Record<string, string>>>;
  // теги по контексту
  tagsByContext: Record<string, Record<string, string[]>>;
}
```

- Ключи `modesByContextProvider[ctx][provider][modeset] = modeId`.
- `tagsByContext[ctx][tagset] = [tagId,...]`.

### 3.2. Модели list‑ответов
Обновить `src/models/mode_sets_list.ts` в соответствии с новой схемой CLI:
- поле `integration: boolean` у ModeSet;
- поле `runs?: Record<string, string>` у Mode.

---

## 4. Изменения UI (Control Panel)

### 4.1. Новый селектор провайдера
Комбобокс провайдера должен быть расположен **до** комбобокса выбора контекста,
так как список доступных контекстов зависит от выбранного провайдера.

Добавить в `media/control.html` + `control.js` + CSS:
- выпадающий список `Provider` (в Control Panel), рядом с контекстом/кнопками или в блоке Adaptive Settings.
- значения берутся из AiIntegrationService (provider.id + provider.name).

### 4.2. Удаление выбора провайдера из Settings
Полностью удалить `lg.ai.provider` из Settings и связанный UI.

Начальный выбор провайдера (когда нет сохранённого состояния) определяется по:
1) детекту `detect()` всех провайдеров;
2) максимальному `priority` среди доступных.

Реальный выбор хранится в ControlPanelState и меняется в UI.

### 4.3. Логика обновления списков
При изменении провайдера должны перезапрашиваться:
- contexts (provider)
- mode‑sets (context + provider)
- tag‑sets (context)

При изменении контекста должны перезапрашиваться:
- mode‑sets (context + provider)
- tag‑sets (context)

---

## 4.4. Генерация/обновление `lg-cfg/ai-interaction.sec.yaml`

### Кнопка в туллбаре
Добавить отдельную action‑кнопку в туллбар Control Panel:
- Название: например **“Update AI Modes Template”**
- Действие: генерация/обновление `lg-cfg/ai-interaction.sec.yaml`.

### Требования к генерации
Перед генерацией Extension должен опросить **все зарегистрированные AI‑провайдеры**:
- какие `runs` они поддерживают;
- к каким пользовательским режимам (ask/agent/plan/…) их разумно применять.

### Merge‑логика
- Обновление **не перетирает** неизвестные/чужие ключи.
- Extension изменяет только те части YAML, которые может объяснить (свои `runs`).
- Если файл уже существует, нужно **добавлять/обновлять** поддерживаемые `runs`, не удаляя остальные.

### Совместимость
Файл должен быть совместим между VS Code и IntelliJ плагинами:
- оба плагина могут обновлять один и тот же `ai-interaction.sec.yaml`;
- если провайдер незнаком плагину, его данные сохраняются как есть.

### Пример содержимого `lg-cfg/ai-interaction.sec.yaml`
Ниже пример **каноничной мета‑секции**, агрегирующей провайдеров из VS Code и IntelliJ.
`runs` — строковые значения, интерпретация которых остаётся на стороне плагина.

```yaml
# lg-cfg/ai-interaction.sec.yaml
ai-interaction:
  title: "AI Interaction"
  mode-sets:
    ai-interaction:
      title: "AI Interaction"
      modes:
        ask:
          title: "Ask"
          description: "Question-answer mode"
          runs:
            com.github.copilot.ext: "workbench.action.chat.openask"
            com.cursor.composer.ext: "cursor.composer.ask"            # пример, зависит от Cursor API
            com.anthropic.claude.cli: "--permission-mode default"
            com.openai.codex.cli: "--sandbox read-only --ask-for-approval on-request"
            com.jetbrains.ai.ext: ""                                  # поддерживается, просто полагаться на дефолты
            org.jetbrains.junie.ext: "ExplicitTaskContext(type=CHAT)" # пример
            com.openai.api: ""                                        # все API-провайдеры по свое природе поддерживают только Ask режим

        agent:
          title: "Agent"
          description: "Agent mode with tools"
          tags: [agent]
          runs:
            com.github.copilot.ext: "workbench.action.chat.openagent"
            com.cursor.composer.ext: "cursor.composer.agent"          # пример
            com.anthropic.claude.cli: "--permission-mode acceptEdits"
            com.openai.codex.cli: "--sandbox workspace-write --ask-for-approval on-request"
            com.jetbrains.ai.ext: "currentChatMode.setChatMode(\"CodeGeneration\")" # пример, зависит от IntelliJ API
            org.jetbrains.junie.ext: "ExplicitTaskContext(type=ISSUE)"

        plan:
          title: "Plan"
          description: "Planning / specification mode"
          tags: [agent, plan]
          runs:
            com.github.copilot.ext: "workbench.action.chat.openplan"
            com.anthropic.claude.cli: "--permission-mode plan"
            # com.openai.codex.cli — пока не поддерживается (пример намеренно отсутствует)
```

Примечания:
- Значения `runs` **примерные**. Плагин обязан подставлять те значения, которые он реально поддерживает.
- Если провайдер не поддерживает режим — ключ `runs[provider]` **не добавляется**.

---

## 5. Интеграция с CLI

### 5.1. Новые вызовы
Обновить `cliList` и `CatalogService`:

```
list contexts  [--provider <provider>]
list mode-sets --context <ctx> --provider <provider>
list tag-sets  --context <ctx>
```

### 5.2. CLI args для render/report
`buildCliArgs()` должен:
- передавать `--provider <currentProvider>`;
- брать modes из `modesByContextProvider[currentContext][currentProvider]`;
- брать tags из `tagsByContext[currentContext]`.

Аргумент `--provider` используется CLI для:
- оценки условий `provider:<base-id>` в шаблонах (нормализация: отсечение суффикса `.cli`/`.ext`/`.api`);
- не влияет на фильтрацию файлов.

Провайдер `clipboard` является универсальным — совместим со всеми контекстами и режимами.
При выборе `clipboard` фильтрация контекстов и режимов не производится.

---

## 6. Работа с `runs` и режимами

### 6.1. Правило единственного интеграционного набора
UI должен ожидать от CLI **ровно один интеграционный набор**. Если его нет — показывать ошибку пользователю.

### 6.2. Исполнение `runs`

#### Extension‑провайдеры (Copilot/Cursor и т.п.)
- `runs` трактуется как идентификатор VS Code команды.
- Использовать `vscode.commands.executeCommand(runs)`.

#### CLI‑провайдеры (Claude/Codex)
- `runs` — строка флагов (provider‑specific).
- Парсить строку на стороне провайдера.

Пример разборов:
- Claude CLI: `--permission-mode plan|acceptEdits|default`.
- Codex CLI: `--sandbox read-only|workspace-write`, `--ask-for-approval on-request`.

Результат парсинга используется при создании session file/команды (вместо старого AiInteractionMode).

### 6.3. Удаление `AiInteractionMode`
- Модель `AiInteractionMode` и все места её использования должны быть удалены/заменены.
- Новый интерфейс отправки должен принимать `runs` напрямую.

---

## 7. Изменения в коде

### 7.1. ControlStateService
- новая структура state;
- методы `getCurrentModes(ctx, provider)` и `getCurrentTags(ctx)`;
- обновить `actualizeState()` под новый формат;
- хранить `providerId`.

### 7.2. ControlPanelView
- передавать `providerId` в webview;
- перезапрашивать списки при смене provider или template;
- обновить CLI settings block (видимость зависит от выбранного providerId, а не Settings).

### 7.3. Webview (`control.js`)
- добавить UI для выбора провайдера;
- хранить в state `providerId`;
- при изменении контекста/провайдера — запрос новых mode‑sets/tag‑sets.

### 7.4. AiIntegrationService
- вместо `getAiInteractionMode()` использовать `getIntegrationModeRuns()`.
- `sendToProvider(providerId, content, runs)`.

### 7.5. Providers
- Copilot/Cursor: использовать `runs` как command id.
- Claude/Codex: парсить `runs` и применять параметры запуска.

---

## 8. Безопасность

- При наличии неизвестного providerId в `runs` или нестандартных флагов — показывать предупреждение.
- Подтверждение пользователя перед первым запуском таких `runs` в репозитории.

---

## 9. Тесты/проверки

Минимум:
1) Смена context → обновление mode‑sets/tag‑sets.
2) Смена provider → обновление mode‑sets + корректный фильтр интеграционного набора.
3) Отправка в AI использует `runs`.
4) Актуализация state при изменении lg‑cfg.
5) Ошибка при отсутствии интеграционного набора.

---

## 10. Рефакторинги

- Удалить `AiInteractionMode` и связанный маппинг в providers.
- Централизовать парсинг `runs` для CLI‑провайдеров (общая утилита в `src/services/ai/providers/*`).

---

## 11. Выходные артефакты

- Обновлённая Control Panel UI (provider selector).
- Новый state‑модуль с пер‑контекстным хранением.
- Обновлённые интеграции с AI через `runs`.
- Поддержка новых list‑команд CLI.

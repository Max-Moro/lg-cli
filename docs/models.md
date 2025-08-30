# Конфигурирование AI-моделей

Этот раздел объясняет, **как выбрать и настроить модель** для расчёта токенов и лимитов окна контекста в Listing Generator (LG). Настройка модели влияет **только на статистику** (`tokens*`, `ctxShare`, «переполнение окна») и выбор энкодера для токенизации. На состав финального текста это не влияет.

---

## Быстрый пример: `lg-cfg/models.yaml`

```yaml
models:
  # Базовые «физические» модели: провайдер, окно контекста, энкодер для токенизации
  o3:
    provider: openai
    ctx_limit: 200000
    encoder: gpt-4o

  gpt-4o:
    provider: openai
    ctx_limit: 128000
    encoder: gpt-4o

  claude-3.5-sonnet:
    provider: anthropic
    ctx_limit: 200000
    encoder: cl100k_base

  gemini-2.5-pro:
    provider: google
    ctx_limit: 1000000
    encoder: cl100k_base

# Необязательные «планы» — маркетинговые колпаки приложений (ChatGPT, Claude, Gemini Apps).
# Эффективный лимит = min(model.ctx_limit, plan.ctx_cap)
plans:
  - name: Plus/Team
    provider: openai
    ctx_cap: 32000
    featured: true

  - name: Pro
    provider: openai
    ctx_cap: 128000
    featured: true

  - name: Pro
    provider: google
    ctx_cap: 1000000
    featured: true
```

> Если `lg-cfg/models.yaml` отсутствует, LG использует встроенные дефолты (OpenAI/Anthropic/Google/Cohere) с разумными значениями энкодеров и лимитов.

---

## Как выбрать модель при запуске

Укажите модель флагом `--model` в `render`/`report`:

```bash
# База (без плана)
lg report ctx:my-context --model o3 > report.json

# Та же база, но с «колпаком» ChatGPT Plus/Team (32k)
lg report ctx:my-context --model o3__plusteam > report.json
```

**Идентификатор модели** имеет вид:

* `<base>` — имя из `models:` (например, `o3`, `gpt-4o`, `gemini-2.5-pro`);
* `<base>__<plan-slug>` — когда хотите учесть «план» приложения.
  Слаг формируется так: нижний регистр, пробелы/подчёркивания → `-`,
  не буквенно-цифровые символы удаляются, повторные `-` схлопываются.
  Примеры:
  `Plus/Team → plusteam`, `Enterprise → enterprise`, `Pro → pro`.

Посмотреть доступные варианты можно так:

```bash
lg list models
# → JSON: массив объектов {id, label, base, plan, provider, encoder, ctxLimit}
```

---

## Что такое «модели» и «планы» в LG

* **Модель (`models:`)** — «физическое» окно провайдера и выбранный энкодер токенов (`tiktoken`).
  Пример: `gpt-4o` с `ctx_limit: 128000` и `encoder: gpt-4o`.

* **План (`plans:`)** — ограничение со стороны **клиентского приложения** (ChatGPT/Claude/Gemini Apps).
  Например, ChatGPT Plus/Team даёт \~32k в чате, даже если базовая модель умеет больше.

**Итоговый лимит**, который LG использует в отчёте, равен:

```
effective_ctx_limit = min(model.ctx_limit, plan.ctx_cap?)  # если план не задан → просто model.ctx_limit
```

Это значение попадает в:

* `encoder` — имя энкодера для токенизации,
* `ctxLimit` — предел окна,
* `total.ctxShare` и `context.finalCtxShare` — доля окна, занятого итогом.

---

## Пояснение полей `models.yaml`

* `models.<alias>.provider` — строка: `openai|anthropic|google|cohere|…` (произвольно).

* `models.<alias>.ctx_limit` — максимальное окно контекста **в токенах** для базовой модели.

* `models.<alias>.encoder` — имя энкодера для `tiktoken`.
  Рекомендации:

  * OpenAI: `gpt-4o` или `o200k_base` (для больших окон).
  * Anthropic/Google/Cohere: используйте `cl100k_base` как стабильный дефолт.
    Если энкодер неизвестен, LG аккуратно откатится к `cl100k_base`.

* `plans[].name` — отображаемое имя плана в отчётах (например, `Plus/Team`, `Pro`).

* `plans[].provider` — к какому провайдеру относится план (должен совпадать с `models.*.provider`).

* `plans[].ctx_cap` — лимит окна **в клиентах** (чат-приложениях).

* `plans[].featured` — помечает план как «избранный», чтобы показывать его в `lg list models`.


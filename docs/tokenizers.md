# Listing Generator · _Токенизация и расчет статистики_

Listing Generator поддерживает несколько опенсорсных библиотек токенизации для расчета статистики по токенам в ваших контекстах и промтах.

---

## Философия подхода

LG **не привязывается к конкретным продуктовым LLM-моделям**. Причины:

1. **Быстрое устаревание**: новые версии моделей выходят почти каждый месяц (GPT-4 → GPT-4o → o1 → o3, Claude 3.5 → Claude 4 и т.д.)
2. **Разнообразие провайдеров**: разные пользователи работают с разными моделями в зависимости от задач, бюджета и лицензий
3. **Множество клиентов**: одна и та же модель может иметь разные лимиты в зависимости от используемого клиента (IDE, CLI, веб-интерфейс, тарифный план)

**Решение LG**: вы явно указываете **библиотеку токенизации**, **энкодер/алгоритм** и **размер контекстного окна** при каждом запуске. Это делает статистику прозрачной и актуальной для вашей текущей ситуации.

---

## Поддерживаемые библиотеки

LG интегрирует три опенсорсные библиотеки токенизации:

### 1. tiktoken (OpenAI)

**Описание**: Официальная библиотека токенизации OpenAI, используется в GPT-моделях. Очень быстрая (реализация на C).

**Встроенные энкодеры**:
- `gpt2` - старые GPT-2 модели
- `r50k_base` - Codex модели
- `p50k_base` - GPT-3 модели (text-davinci-002, text-davinci-003)
- `cl100k_base` - GPT-3.5, GPT-4, GPT-4 Turbo
- `o200k_base` - GPT-4o, o1, o3, o4-mini

**Особенности**:
- Не требует скачивания моделей (все встроено)
- Самый быстрый вариант для OpenAI моделей
- Можно использовать для приближенного подсчета токенов других моделей

### 2. tokenizers (HuggingFace)

**Описание**: Универсальная библиотека токенизации от HuggingFace (реализация на Rust). Поддерживает множество алгоритмов и предобученных токенизаторов.

**Предобученные токенизаторы** (рекомендуемые универсальные):
- `gpt2` - GPT-2 BPE
- `roberta-base` - RoBERTa BPE
- `bert-base-uncased` - BERT WordPiece
- `bert-base-cased` - BERT WordPiece (case-sensitive)
- `t5-base` - T5 SentencePiece-based
- `google/gemma-tokenizer` - Gemma (Google)

**Особенности**:
- Модели скачиваются с HuggingFace Hub при первом использовании
- Кешируются в `lg-cfg/tokenizer-models/tokenizers/`
- Можно указать любую модель с HF Hub (не только из списка)

### 3. sentencepiece (Google)

**Описание**: Библиотека токенизации от Google, используется в Gemini и многих открытых моделях (Llama, T5 и др.).

**Рекомендуемые модели**:
- `google/gemma-2-2b` - Gemma токенизатор (универсальный)
- `meta-llama/Llama-2-7b-hf` - Llama 2 токенизатор

**Особенности**:
- Модели (файлы `.model`/`.spm`) скачиваются с HuggingFace Hub
- Кешируются в `lg-cfg/tokenizer-models/sentencepiece/`
- Можно указать путь к локальному файлу: `/path/to/model.spm`

---

## Использование

### Основной синтаксис

При вызове команд `render` или `report` укажите три обязательных параметра:

```bash
lg render ctx:all \
  --lib <tiktoken|tokenizers|sentencepiece> \
  --encoder <имя_энкодера> \
  --ctx-limit <размер_окна_в_токенах>
```

### Примеры

#### Использование tiktoken (OpenAI)

```bash
# GPT-4, GPT-3.5 Turbo
lg report ctx:all \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000

# GPT-4o, o1, o3
lg report ctx:all \
  --lib tiktoken \
  --encoder o200k_base \
  --ctx-limit 200000
```

#### Использование tokenizers (HuggingFace)

```bash
# Первый запуск - автоматически скачает модель
lg report ctx:all \
  --lib tokenizers \
  --encoder gpt2 \
  --ctx-limit 50000

# Модель из HF Hub (произвольная)
lg report ctx:all \
  --lib tokenizers \
  --encoder google/gemma-tokenizer \
  --ctx-limit 100000
```

#### Использование sentencepiece (Google)

```bash
# Gemini приближение
lg report ctx:all \
  --lib sentencepiece \
  --encoder google/gemma-2-2b \
  --ctx-limit 1000000

# Локальный файл модели
lg report ctx:all \
  --lib sentencepiece \
  --encoder /path/to/custom.model \
  --ctx-limit 128000
```

---

## Команды управления

### Список доступных библиотек

```bash
lg list tokenizer-libs
```

**Вывод**:
```json
{
  "tokenizer_libs": ["tiktoken", "tokenizers", "sentencepiece"]
}
```

### Список энкодеров для библиотеки

```bash
# tiktoken (встроенные энкодеры)
lg list encoders --lib tiktoken

# tokenizers (рекомендуемые + скачанные)
lg list encoders --lib tokenizers

# sentencepiece (рекомендуемые + скачанные)
lg list encoders --lib sentencepiece
```

**Пример вывода для tiktoken**:
```json
{
  "lib": "tiktoken",
  "encoders": [
    "gpt2",
    "r50k_base",
    "p50k_base",
    "cl100k_base",
    "o200k_base"
  ]
}
```

**Пример вывода для tokenizers** (после скачивания нескольких моделей):
```json
{
  "lib": "tokenizers",
  "encoders": [
    "gpt2",
    "roberta-base",
    "bert-base-uncased",
    "bert-base-cased",
    "t5-base",
    "google/gemma-tokenizer"
  ]
}
```

---

## Как определить параметры для модели

1. **Поиск в интернете**: найдите информацию о токенизаторе модели
2. **Документация провайдера**: проверьте официальную документацию
3. **HuggingFace Hub**: поищите токенизатор модели на https://huggingface.co/models
4. **Приближение**: если точного токенизатора нет, используйте похожий алгоритм (BPE, WordPiece, Unigram)

**Важно**: для моделей без публичных токенизаторов (Claude, Grok) используются приближения. Статистика будет примерной, но достаточной для оценки размера контекста.

---

## Кеширование моделей

### Где хранятся модели

Скачанные модели токенизации хранятся в:

```
lg-cfg/tokenizer-models/
├── tokenizers/
│   ├── gpt2/
│   ├── bert-base-uncased/
│   └── google--gemma-tokenizer/
└── sentencepiece/
    ├── google--gemma-2-2b/
    └── meta-llama--Llama-2-7b-hf/
```

**Важно**:
- Директория `tokenizer-models/` автоматически добавляется в `.gitignore`
- Модели скачиваются один раз и используются повторно
- При удалении модели она будет скачана заново при следующем использовании

### Управление кешем

```bash
# Просмотр скачанных моделей
ls -la lg-cfg/tokenizer-models/tokenizers/
ls -la lg-cfg/tokenizer-models/sentencepiece/

# Очистка кеша (ручное удаление)
rm -rf lg-cfg/tokenizer-models/tokenizers/bert-base-uncased/

# Полная очистка
rm -rf lg-cfg/tokenizer-models/
```

---

## Размер контекстного окна

Параметр `--ctx-limit` определяет размер контекстного окна в токенах для расчета метрик:
- `ctxShare` - доля окна, занятая файлом/контекстом
- `finalCtxShare` - доля окна, занятая итоговым документом

### Как определить правильный ctx-limit

Размер контекстного окна зависит от **трех факторов**:

1. **Физический лимит модели**: базовое окно контекста модели (например, GPT-4: 128k, Gemini 2.5: 1M)
2. **Лимит тарифного плана**: некоторые провайдеры ограничивают окно в зависимости от подписки
3. **Лимит клиента**: IDE или CLI могут иметь свои ограничения (например, ChatGPT Plus в веб-интерфейсе: 32k)

**Рекомендация**: используйте **минимальное** из этих трех значений, которое соответствует вашей текущей конфигурации.

### Примеры

```bash
# ChatGPT Plus (веб) с GPT-4
# Физический лимит: 128k, лимит веб-клиента: 32k
lg report ctx:all --lib tiktoken --encoder cl100k_base --ctx-limit 32000

# GPT-4o через API (без ограничений плана)
# Физический лимит: 200k, лимит API: 200k
lg report ctx:all --lib tiktoken --encoder o200k_base --ctx-limit 200000

# Claude Pro в веб-клиенте
# Физический лимит: 200k, лимит Pro плана: 200k
lg report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000

# Cursor IDE с Claude Sonnet 4
# Физический лимит: 500k, лимит Cursor: ~200k
lg report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000
```

**Совет**: начните с консервативного значения (например, 128000) и увеличивайте по мере необходимости.

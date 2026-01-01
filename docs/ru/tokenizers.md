# Listing Generator · Токенизация и расчет статистики

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

**Предобученные токенизаторы** (рекомендуемые универсальные, все доступны анонимно):
- `gpt2` - GPT-2 BPE (универсальный для кода и текста)
- `roberta-base` - RoBERTa BPE (улучшенный GPT-2)
- `t5-base` - T5 SentencePiece-based (универсальный)
- `EleutherAI/gpt-neo-125m` - GPT-Neo BPE (открытая альтернатива GPT)
- `microsoft/phi-2` - Phi-2 (современная компактная модель)
- `mistralai/Mistral-7B-v0.1` - Mistral (современная open-source модель)

**Особенности**:
- Модели скачиваются с HuggingFace Hub при первом использовании
- Кешируются в `.lg-cache/tokenizer-models/tokenizers/`
- Можно указать любую модель с HF Hub (не только из списка)
- **Все рекомендуемые модели доступны для анонимного скачивания**
- **Можно указать путь к локальному файлу tokenizer.json или директории с ним**

### 3. sentencepiece (Google)

**Описание**: Библиотека токенизации от Google, используется в Gemini и многих открытых моделях (Llama, T5 и др.).

**Рекомендуемые модели** (все доступны анонимно):
- `t5-small` - T5 Small (компактный, универсальный)
- `t5-base` - T5 Base (больше vocab)
- `google/flan-t5-base` - FLAN-T5 (улучшенный T5, instruction-tuned)
- `google/mt5-base` - mT5 (мультиязычный T5)

**Особенности**:
- Модели (файлы `.model`/`.spm`) скачиваются с HuggingFace Hub
- **Все рекомендуемые модели доступны для анонимного скачивания**
- Подходят для приближенного подсчета токенов Gemini, Claude, Llama
- Кешируются в `.lg-cache/tokenizer-models/sentencepiece/`
- Можно указать путь к локальному файлу: `/path/to/model.spm`

---

## Использование

### Основной синтаксис

При вызове команд `render` или `report` укажите три обязательных параметра:

```bash
listing-generator render ctx:all \
  --lib <tiktoken|tokenizers|sentencepiece> \
  --encoder <имя_энкодера> \
  --ctx-limit <размер_окна_в_токенах>
```

### Примеры

#### Использование tiktoken (OpenAI)

```bash
# GPT-4, GPT-3.5 Turbo
listing-generator report ctx:all \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000

# GPT-4o, o1, o3
listing-generator report ctx:all \
  --lib tiktoken \
  --encoder o200k_base \
  --ctx-limit 200000
```

#### Использование tokenizers (HuggingFace)

```bash
# GPT-2 BPE (универсальный, первый запуск скачает модель)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder gpt2 \
  --ctx-limit 50000

# Mistral (современная open-source модель)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder mistralai/Mistral-7B-v0.1 \
  --ctx-limit 128000

# Локальный файл tokenizer.json
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/tokenizer.json \
  --ctx-limit 128000

# Локальная директория с tokenizer.json внутри
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/model/ \
  --ctx-limit 128000
```

#### Использование sentencepiece (Google)

```bash
# T5 (универсальный, подходит для Gemini/Claude приближения)
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder t5-base \
  --ctx-limit 128000

# FLAN-T5 (instruction-tuned, лучше для промптов)
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder google/flan-t5-base \
  --ctx-limit 1000000

# Локальный файл модели
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder /path/to/custom.model \
  --ctx-limit 128000
```

---

## Команды управления

### Список доступных библиотек

```bash
listing-generator list tokenizer-libs
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
listing-generator list encoders --lib tiktoken

# tokenizers (рекомендуемые + скачанные)
listing-generator list encoders --lib tokenizers

# sentencepiece (рекомендуемые + скачанные)
listing-generator list encoders --lib sentencepiece
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

Для моделей без публичных токенизаторов (Claude, Grok) используются приближения. Статистика будет примерной, но достаточной для оценки размера контекста.

---

## Использование локальных файлов токенизаторов

Для моделей, требующих аутентификацию или лицензионное соглашение на HuggingFace (например, Llama, Gemma), вы можете скачать токенизатор самостоятельно и указать путь к локальному файлу.

При первом использовании локального файла **LG автоматически импортирует его в свой кэш** (`.lg-cache/tokenizer-models/`). Это позволяет в дальнейшем использовать модель по короткому имени без указания полного пути.

### Пример: использование Llama 3.1 токенизатора

```bash
# 1. Скачайте модель с HuggingFace CLI (требуется аутентификация)
huggingface-cli login
huggingface-cli download meta-llama/Llama-3.1-8B --include "tokenizer.json" --local-dir ./llama-tokenizer

# 2. Первое использование - импортирует в кэш LG
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder ./llama-tokenizer/tokenizer.json \
  --ctx-limit 128000
# > Tokenizer imported as 'llama-tokenizer' and available for future use

# 3. Последующие использования - по короткому имени
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder llama-tokenizer \
  --ctx-limit 128000

# Или укажите директорию (LG найдет tokenizer.json внутри)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder ./llama-tokenizer/ \
  --ctx-limit 128000
```

### Пример: использование корпоративного токенизатора

```bash
# Первое использование - импортирует в кэш
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/company/models/custom-tokenizer.json \
  --ctx-limit 200000
# > Tokenizer imported as 'custom-tokenizer' and available for future use

# Теперь можно использовать короткое имя
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder custom-tokenizer \
  --ctx-limit 200000

# Проверить список установленных моделей
listing-generator list encoders --lib tokenizers
# В списке появится 'custom-tokenizer'
```

### Поддерживаемые форматы

**tokenizers (HuggingFace)**:
- Файл `tokenizer.json` напрямую: `/path/to/tokenizer.json`
- Директория с `tokenizer.json` внутри: `/path/to/model/`

**sentencepiece (Google)**:
- Файл модели: `/path/to/model.spm` или `/path/to/tokenizer.model`
- Директория с `.model` файлом внутри: `/path/to/model/`

**tiktoken (OpenAI)**:
- Только встроенные энкодеры (локальные файлы не поддерживаются)

---

## Кеширование моделей

### Где хранятся модели

Скачанные модели токенизации хранятся в:

```
.lg-cache/tokenizer-models/
├── tokenizers/
│   ├── gpt2/
│   ├── bert-base-uncased/
│   └── google--gemma-tokenizer/
└── sentencepiece/
    ├── google--gemma-2-2b/
    └── meta-llama--Llama-2-7b-hf/
```

**Важно**:
- Директория `.lg-cache/` автоматически добавляется в корневой `.gitignore`
- Модели скачиваются один раз и используются повторно
- При удалении модели она будет скачана заново при следующем использовании

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
listing-generator report ctx:all --lib tiktoken --encoder cl100k_base --ctx-limit 32000

# GPT-4o через API (без ограничений плана)
# Физический лимит: 200k, лимит API: 200k
listing-generator report ctx:all --lib tiktoken --encoder o200k_base --ctx-limit 200000

# Claude Pro в веб-клиенте
# Физический лимит: 200k, лимит Pro плана: 200k
listing-generator report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000

# Cursor IDE с Claude Sonnet 4
# Физический лимит: 500k, лимит Cursor: ~200k
listing-generator report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000
```

# Listing Generator · Tokenization and Statistics Calculation

Listing Generator supports several open-source tokenization libraries for calculating token statistics in your contexts and prompts.

---

## Design Philosophy

LG **is not tied to specific production LLM models**. Reasons:

1. **Rapid obsolescence**: new model versions are released almost every month (GPT-4 → GPT-4o → o1 → o3, Claude 3.5 → Claude 4, etc.)
2. **Provider diversity**: different users work with different models depending on tasks, budget, and licenses
3. **Multiple clients**: the same model may have different limits depending on the client used (IDE, CLI, web interface, pricing plan)

**LG's solution**: you explicitly specify the **tokenization library**, **encoder/algorithm**, and **context window size** for each run. This makes statistics transparent and relevant to your current situation.

---

## Supported Libraries

LG integrates three open-source tokenization libraries:

### 1. tiktoken (OpenAI)

**Description**: Official OpenAI tokenization library, used in GPT models. Very fast (C implementation).

**Built-in encoders**:
- `gpt2` - older GPT-2 models
- `r50k_base` - Codex models
- `p50k_base` - GPT-3 models (text-davinci-002, text-davinci-003)
- `cl100k_base` - GPT-3.5, GPT-4, GPT-4 Turbo
- `o200k_base` - GPT-4o, o1, o3, o4-mini

**Features**:
- No model downloads required (everything is built-in)
- Fastest option for OpenAI models
- Can be used for approximate token counting with other models

### 2. tokenizers (HuggingFace)

**Description**: Universal tokenization library from HuggingFace (Rust implementation). Supports many algorithms and pre-trained tokenizers.

**Pre-trained tokenizers** (recommended universal ones, all available anonymously):
- `gpt2` - GPT-2 BPE (universal for code and text)
- `roberta-base` - RoBERTa BPE (improved GPT-2)
- `t5-base` - T5 SentencePiece-based (universal)
- `EleutherAI/gpt-neo-125m` - GPT-Neo BPE (open alternative to GPT)
- `microsoft/phi-2` - Phi-2 (modern compact model)
- `mistralai/Mistral-7B-v0.1` - Mistral (modern open-source model)

**Features**:
- Models are downloaded from HuggingFace Hub on first use
- Cached in `.lg-cache/tokenizer-models/tokenizers/`
- You can specify any model from HF Hub (not just from the list)
- **All recommended models are available for anonymous download**
- **You can specify a path to a local tokenizer.json file or directory containing it**

### 3. sentencepiece (Google)

**Description**: Tokenization library from Google, used in Gemini and many open models (Llama, T5, etc.).

**Recommended models** (all available anonymously):
- `t5-small` - T5 Small (compact, universal)
- `t5-base` - T5 Base (larger vocab)
- `google/flan-t5-base` - FLAN-T5 (improved T5, instruction-tuned)
- `google/mt5-base` - mT5 (multilingual T5)

**Features**:
- Models (`.model`/`.spm` files) are downloaded from HuggingFace Hub
- **All recommended models are available for anonymous download**
- Suitable for approximate token counting for Gemini, Claude, Llama
- Cached in `.lg-cache/tokenizer-models/sentencepiece/`
- You can specify a path to a local file: `/path/to/model.spm`

---

## Usage

### Basic Syntax

When calling `render` or `report` commands, specify three required parameters:

```bash
listing-generator render ctx:all \
  --lib <tiktoken|tokenizers|sentencepiece> \
  --encoder <encoder_name> \
  --ctx-limit <window_size_in_tokens>
```

### Examples

#### Using tiktoken (OpenAI)

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

#### Using tokenizers (HuggingFace)

```bash
# GPT-2 BPE (universal, first run will download the model)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder gpt2 \
  --ctx-limit 50000

# Mistral (modern open-source model)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder mistralai/Mistral-7B-v0.1 \
  --ctx-limit 128000

# Local tokenizer.json file
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/tokenizer.json \
  --ctx-limit 128000

# Local directory with tokenizer.json inside
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/model/ \
  --ctx-limit 128000
```

#### Using sentencepiece (Google)

```bash
# T5 (universal, suitable for Gemini/Claude approximation)
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder t5-base \
  --ctx-limit 128000

# FLAN-T5 (instruction-tuned, better for prompts)
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder google/flan-t5-base \
  --ctx-limit 1000000

# Local model file
listing-generator report ctx:all \
  --lib sentencepiece \
  --encoder /path/to/custom.model \
  --ctx-limit 128000
```

---

## Management Commands

### List Available Libraries

```bash
listing-generator list tokenizer-libs
```

**Output**:
```json
{
  "tokenizer_libs": ["tiktoken", "tokenizers", "sentencepiece"]
}
```

### List Encoders for a Library

```bash
# tiktoken (built-in encoders)
listing-generator list encoders --lib tiktoken

# tokenizers (recommended + downloaded)
listing-generator list encoders --lib tokenizers

# sentencepiece (recommended + downloaded)
listing-generator list encoders --lib sentencepiece
```

**Example output for tiktoken**:
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

**Example output for tokenizers** (after downloading several models):
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

## How to Determine Parameters for a Model

1. **Internet search**: find information about the model's tokenizer
2. **Provider documentation**: check official documentation
3. **HuggingFace Hub**: search for the model's tokenizer at https://huggingface.co/models
4. **Approximation**: if there's no exact tokenizer, use a similar algorithm (BPE, WordPiece, Unigram)

For models without public tokenizers (Claude, Grok), approximations are used. Statistics will be approximate, but sufficient for context size estimation.

---

## Using Local Tokenizer Files

For models requiring authentication or license agreements on HuggingFace (e.g., Llama, Gemma), you can download the tokenizer yourself and specify the path to the local file.

When using a local file for the first time, **LG automatically imports it into its cache** (`.lg-cache/tokenizer-models/`). This allows you to use the model by its short name in the future without specifying the full path.

### Example: Using Llama 3.1 Tokenizer

```bash
# 1. Download the model with HuggingFace CLI (authentication required)
huggingface-cli login
huggingface-cli download meta-llama/Llama-3.1-8B --include "tokenizer.json" --local-dir ./llama-tokenizer

# 2. First use - imports into LG cache
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder ./llama-tokenizer/tokenizer.json \
  --ctx-limit 128000
# > Tokenizer imported as 'llama-tokenizer' and available for future use

# 3. Subsequent uses - by short name
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder llama-tokenizer \
  --ctx-limit 128000

# Or specify a directory (LG will find tokenizer.json inside)
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder ./llama-tokenizer/ \
  --ctx-limit 128000
```

### Example: Using Corporate Tokenizer

```bash
# First use - imports into cache
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder /path/to/company/models/custom-tokenizer.json \
  --ctx-limit 200000
# > Tokenizer imported as 'custom-tokenizer' and available for future use

# Now you can use the short name
listing-generator report ctx:all \
  --lib tokenizers \
  --encoder custom-tokenizer \
  --ctx-limit 200000

# Check the list of installed models
listing-generator list encoders --lib tokenizers
# 'custom-tokenizer' will appear in the list
```

### Supported Formats

**tokenizers (HuggingFace)**:
- `tokenizer.json` file directly: `/path/to/tokenizer.json`
- Directory with `tokenizer.json` inside: `/path/to/model/`

**sentencepiece (Google)**:
- Model file: `/path/to/model.spm` or `/path/to/tokenizer.model`
- Directory with `.model` file inside: `/path/to/model/`

**tiktoken (OpenAI)**:
- Only built-in encoders (local files not supported)

---

## Model Caching

### Where Models Are Stored

Downloaded tokenization models are stored in:

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

**Important**:
- The `.lg-cache/` directory is automatically added to the root `.gitignore`
- Models are downloaded once and reused
- If a model is deleted, it will be re-downloaded on next use

---

## Context Window Size

The `--ctx-limit` parameter defines the context window size in tokens for metric calculations:
- `ctxShare` - fraction of the window occupied by the file/context
- `finalCtxShare` - fraction of the window occupied by the final document

### How to Determine the Correct ctx-limit

The context window size depends on **three factors**:

1. **Physical model limit**: the model's base context window (e.g., GPT-4: 128k, Gemini 2.5: 1M)
2. **Pricing plan limit**: some providers limit the window based on subscription
3. **Client limit**: IDEs or CLIs may have their own limitations (e.g., ChatGPT Plus in web interface: 32k)

**Recommendation**: use the **minimum** of these three values that corresponds to your current configuration.

### Examples

```bash
# ChatGPT Plus (web) with GPT-4
# Physical limit: 128k, web client limit: 32k
listing-generator report ctx:all --lib tiktoken --encoder cl100k_base --ctx-limit 32000

# GPT-4o via API (no plan restrictions)
# Physical limit: 200k, API limit: 200k
listing-generator report ctx:all --lib tiktoken --encoder o200k_base --ctx-limit 200000

# Claude Pro in web client
# Physical limit: 200k, Pro plan limit: 200k
listing-generator report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000

# Cursor IDE with Claude Sonnet 4
# Physical limit: 500k, Cursor limit: ~200k
listing-generator report ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 200000
```

# Test Resources: Tokenizer Models

This directory contains pre-downloaded tokenizer models used in tests to avoid downloading them from HuggingFace Hub during test runs.

## Structure

```
resources/
├── models_manifest.json       # Manifest with model information
├── tokenizers/                # HuggingFace tokenizers models
│   └── gpt2/
│       └── tokenizer.json
└── sentencepiece/             # SentencePiece models
    └── google--gemma-2-2b/
        └── tokenizer.model
```

## Setup Instructions

### 1. Download GPT-2 Tokenizer

```bash
python -c "
from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download
import shutil
from pathlib import Path

# Download tokenizer
tokenizer_file = hf_hub_download(repo_id='gpt2', filename='tokenizer.json')

# Copy to resources
target = Path('tests/stats/resources/tokenizers/gpt2/')
target.mkdir(parents=True, exist_ok=True)
shutil.copy(tokenizer_file, target / 'tokenizer.json')
print(f'Downloaded to {target}')
"
```

### 2. Download Gemma Tokenizer

```bash
python -c "
from huggingface_hub import hf_hub_download
import shutil
from pathlib import Path

# Download tokenizer
tokenizer_file = hf_hub_download(
    repo_id='google/gemma-2-2b',
    filename='tokenizer.model'
)

# Copy to resources
target = Path('tests/stats/resources/sentencepiece/google--gemma-2-2b/')
target.mkdir(parents=True, exist_ok=True)
shutil.copy(tokenizer_file, target / 'tokenizer.model')
print(f'Downloaded to {target}')
"
```

## Adding New Models

1. Update `models_manifest.json` with model information
2. Create appropriate subdirectory structure
3. Download and place model files
4. Update this README with download instructions

## Important Notes

- These files are **NOT** included in git (see `.gitignore`)
- Each developer needs to run setup instructions once
- Models are cached locally to speed up tests
- Mock in `conftest.py` uses these files instead of downloading

## Alternatives

If you don't want to download models manually, tests will attempt to use tiktoken (which doesn't require downloads) as fallback where possible.

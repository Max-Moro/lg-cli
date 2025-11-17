# Test Infrastructure for Statistics and Tokenization

## Overview

A complete infrastructure has been created for testing the statistics and tokenization subsystem in Listing Generator. The infrastructure allows:

- Testing various tokenizers without downloading models on each run
- Verifying model caching correctness
- Comparing accuracy of different tokenizers
- Checking statistics calculation and token optimizations

## Structure

```
tests/
└── stats/                           # New test package
    ├── __init__.py                  # Package description
    ├── conftest.py                  # Fixtures and mock for HF Hub
    ├── SETUP.md                     # Setup instructions
    ├── download_test_models.py      # Model download script
    │
    ├── resources/                   # Pre-downloaded models
    │   ├── models_manifest.json     # Models manifest
    │   ├── tokenizers/              # HuggingFace tokenizers
    │   │   └── gpt2/
    │   │       └── tokenizer.json   # (downloaded separately)
    │   └── sentencepiece/           # SentencePiece models
    │       └── t5-small/
    │           └── tokenizer.model  # (downloaded separately)
    │
    ├── test_model_cache.py          # Model caching tests
    ├── test_tokenizer_comparison.py # Tokenizer comparisons
    └── test_statistics.py           # Main statistics tests
```

## Key Components

### 1. Mock for HuggingFace Hub (`conftest.py`)

The `mock_hf_hub` fixture replaces `hf_hub_download` with a version that:
- Uses pre-downloaded models from `resources/`
- Mimics real HF Hub behavior
- Tracks number of "downloads" for cache tests
- Automatically activates for all tests in the package

### 2. Tokenizer Fixtures

- `tiktoken_service` - always available (built-in)
- `hf_tokenizer_service` - requires models in resources/
- `sp_tokenizer_service` - requires models in resources/
- `sample_texts` - set of test texts for comparisons

### 3. Tests

#### `test_model_cache.py`
Verifies that `lg.stats.tokenizers.model_cache.ModelCache`:
- Correctly creates cache structure
- Safely handles names with `/` (converts to `--`)
- Properly determines model presence in cache
- List of cached models is correct
- Cache survives program restarts
- Adapters use cache and don't re-download models

#### `test_tokenizer_comparison.py`
Verifies that:
- All tokenizers correctly count tokens
- Different tokenizers give different results
- Results are stable for the same text
- Tokenization is efficient for code and mixed content
- Special characters are handled correctly
- Difference between tokenizers is within reasonable limits
- Token caching works properly

#### `test_statistics.py`
Rewritten tests from old `test_stats.py`:
- Markdown optimizations (H1 removal, token savings)
- Rendering overheads (fences, file markers)
- Context template overheads
- Share distribution in prompt
- Metadata aggregation
- Statistics at individual file level

## Usage

### Quick Start (tiktoken only)

```bash
pytest tests/stats/
```

Tests automatically use tiktoken (built-in) when HF/SP models are unavailable.

### Full Environment

```bash
# 1. Install dependencies
pip install tokenizers sentencepiece huggingface-hub

# 2. Download test models
python tests/stats/download_test_models.py

# 3. Run all tests
pytest tests/stats/ -v
```

### CI/CD

In CI environment (without models):
- Tests use only tiktoken
- Tests requiring HF/SP are skipped
- Basic functionality is fully tested

For complete testing:
- Download models once
- Cache `tests/stats/resources/`
- Reuse in subsequent runs

## Important Changes

### Removed
- `tests/test_stats.py` (old file, replaced by `tests/stats/test_statistics.py`)

### Added
- `tests/stats/` - new test package
- Mock for HuggingFace Hub without real downloading
- Automatic model download script
- Detailed setup documentation
- Use of constants from `cli_utils` to avoid hardcoding

### Updated
- Old statistics tests completely rewritten for new infrastructure
- Fixtures use default values from infrastructure

## New Infrastructure Benefits

1. **Fast tests**: models are not downloaded on each run
2. **Offline operation**: tests work without internet (after initial setup)
3. **Determinism**: same models in each run
4. **Extensibility**: easy to add new tokenizers
5. **CI-friendly**: works with and without models
6. **Reusability**: utilities available to all tests

## Next Steps

To complete setup:

1. Download test models:
   ```bash
   python tests/stats/download_test_models.py
   ```

2. Run tests for verification:
   ```bash
   pytest tests/stats/ -v
   ```

3. Verify caching works:
   - First run: models "downloading"
   - Subsequent runs: "Loading from cache"

4. (Optional) Add to CI:
   - Cache `tests/stats/resources/`
   - Or use tiktoken-only tests

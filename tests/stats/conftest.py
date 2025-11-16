"""
Fixtures and utilities for statistics and tokenization tests.

Provides:
- mock for hf_hub_download (uses pre-downloaded models from resources/)
- fixtures for creating tokenizers
- helpers for working with model cache
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import pytest


# ==================== Resource Paths ====================

@pytest.fixture(scope="session")
def resources_dir() -> Path:
    """Directory with pre-downloaded models for tests."""
    return Path(__file__).parent / "resources"


@pytest.fixture(scope="session")
def models_manifest(resources_dir: Path) -> dict:
    """
    Manifest with information about pre-downloaded models.

    Format:
    {
        "tokenizers": {
            "gpt2": {"filename": "tokenizer.json", "description": "..."},
            ...
        },
        "sentencepiece": {
            "google/gemma-2-2b": {"filename": "tokenizer.model", "description": "..."},
            ...
        }
    }
    """
    manifest_file = resources_dir / "models_manifest.json"
    if not manifest_file.exists():
        return {"tokenizers": {}, "sentencepiece": {}}

    with manifest_file.open("r", encoding="utf-8") as f:
        return json.load(f)


# ==================== Mock for HuggingFace Hub ====================

class MockHFHub:
    """Mock for hf_hub_download using local resources."""

    def __init__(self, resources_dir: Path, manifest: dict):
        self.resources_dir = resources_dir
        self.manifest = manifest
        self.download_count = 0

    def download(
        self,
        repo_id: str,
        filename: str,
        cache_dir: Optional[str] = None,
        local_dir: Optional[str] = None,
        local_dir_use_symlinks: bool = False,
        **kwargs
    ) -> str:
        """
        Simulates hf_hub_download but returns files from resources/.

        Copies model from resources/ to cache_dir to simulate real behavior.
        """
        self.download_count += 1

        # Determine library type by filename
        if filename == "tokenizer.json":
            lib_type = "tokenizers"
        elif filename in ("tokenizer.model", "spiece.model", "sentencepiece.model"):
            lib_type = "sentencepiece"
        else:
            raise FileNotFoundError(f"Unknown model file type: {filename}")

        # Check if model is in manifest
        models = self.manifest.get(lib_type, {})
        if repo_id not in models:
            available = list(models.keys())
            raise FileNotFoundError(
                f"Model '{repo_id}' not found in test resources for {lib_type}. "
                f"Available models: {available if available else '(none)'}"
            )

        model_info = models[repo_id]
        source_file = self.resources_dir / lib_type / repo_id.replace("/", "--") / model_info["filename"]

        if not source_file.exists():
            raise FileNotFoundError(f"Model file not found in resources: {source_file}")

        # Copy to cache_dir (if specified)
        if local_dir:
            target_dir = Path(local_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            shutil.copy2(source_file, target_file)
            return str(target_file)
        elif cache_dir:
            target_dir = Path(cache_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            shutil.copy2(source_file, target_file)
            return str(target_file)
        else:
            # Without cache - just return path to file in resources
            return str(source_file)


@pytest.fixture
def mock_hf_hub(resources_dir: Path, models_manifest: dict, monkeypatch):
    """
    Replaces hf_hub_download with mock using local resources.

    Usage in tests:
        def test_something(mock_hf_hub):
            # hf_hub_download now uses local models
            adapter = HFAdapter("gpt2", tmp_path)
            ...

            # Can check how many times the model was downloaded
            assert mock_hf_hub.download_count == 1
    """
    mock = MockHFHub(resources_dir, models_manifest)

    # Patch hf_hub_download in both adapters
    monkeypatch.setattr(
        "lg.stats.tokenizers.hf_adapter.hf_hub_download",
        mock.download
    )
    monkeypatch.setattr(
        "lg.stats.tokenizers.sp_adapter.hf_hub_download",
        mock.download
    )

    return mock


# ==================== Tokenizer Fixtures ====================

@pytest.fixture
def tiktoken_service(tmp_path: Path):
    """Creates TokenService with tiktoken encoder (default settings)."""
    from lg.stats.tokenizer import TokenService
    from tests.infrastructure.cli_utils import DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER

    return TokenService(
        root=tmp_path,
        lib=DEFAULT_TOKENIZER_LIB,
        encoder=DEFAULT_ENCODER
    )


@pytest.fixture
def hf_tokenizer_service(tmp_path: Path, mock_hf_hub):
    """Creates TokenService with HuggingFace tokenizer."""
    from lg.stats.tokenizer import TokenService

    return TokenService(
        root=tmp_path,
        lib="tokenizers",
        encoder="gpt2"  # Simple model for tests
    )


@pytest.fixture
def sp_tokenizer_service(tmp_path: Path, mock_hf_hub):
    """Creates TokenService with SentencePiece tokenizer."""
    from lg.stats.tokenizer import TokenService

    return TokenService(
        root=tmp_path,
        lib="sentencepiece",
        encoder="t5-small"  # Available model without authorization
    )


# ==================== Test Text Fixture ====================

@pytest.fixture
def sample_texts() -> dict:
    """
    Set of test texts for comparing tokenizers.

    Includes:
    - Simple English text
    - Python code
    - Mixed content
    - Special characters
    """
    return {
        "simple": "Hello, world! This is a test.",
        "python_code": '''
def hello_world():
    """Prints hello world."""
    print("Hello, world!")
    return 42
'''.strip(),
        "mixed": '''
# Documentation

Here is some Python code:

```python
def process_data(items):
    return [x * 2 for x in items]
```

And some explanation text.
'''.strip(),
        "special_chars": "Special: ñ, ü, 你好, emoji 🚀, symbols @#$%",
        "long_text": " ".join(["This is a longer text with repeated words."] * 50),
    }


# ==================== Utilities ====================

@pytest.fixture
def clear_model_cache(tmp_path: Path):
    """Clears model cache before each test."""
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

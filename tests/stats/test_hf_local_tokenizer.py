"""
Tests for support of local HuggingFace tokenizer files.
"""

import json

import pytest

from lg.stats.tokenizers import HFAdapter


@pytest.fixture
def simple_tokenizer_json():
    """Creates simple valid tokenizer.json for tests."""
    # Minimal valid tokenizer (BPE)
    tokenizer_config = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": [],
        "normalizer": None,
        "pre_tokenizer": {
            "type": "ByteLevel",
            "add_prefix_space": False,
            "trim_offsets": True,
            "use_regex": True
        },
        "post_processor": None,
        "decoder": {
            "type": "ByteLevel",
            "add_prefix_space": True,
            "trim_offsets": True,
            "use_regex": True
        },
        "model": {
            "type": "BPE",
            "dropout": None,
            "unk_token": None,
            "continuing_subword_prefix": None,
            "end_of_word_suffix": None,
            "fuse_unk": False,
            "byte_fallback": False,
            "vocab": {
                "a": 0,
                "b": 1,
                "c": 2,
                "ab": 3,
                "bc": 4
            },
            "merges": [
                "a b",
                "b c"
            ]
        }
    }
    return tokenizer_config


def test_load_from_local_file(simple_tokenizer_json, tmp_path):
    """Test loading tokenizer from local file."""
    # Create temporary tokenizer.json file
    tokenizer_file = tmp_path / "tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)

    # Load tokenizer from file
    adapter = HFAdapter(str(tokenizer_file), tmp_path)

    # Check that tokenizer works
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0

    # Check encode/decode
    tokens = adapter.encode(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0

    decoded = adapter.decode(tokens)
    assert isinstance(decoded, str)

    # Check that model appeared in available list
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "tokenizer" in available  # filename without extension


def test_load_from_local_directory(simple_tokenizer_json, tmp_path):
    """Test loading tokenizer from directory."""
    # Create directory with tokenizer.json
    model_dir = tmp_path / "my_model"
    model_dir.mkdir()

    tokenizer_file = model_dir / "tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)

    # Load tokenizer from directory
    adapter = HFAdapter(str(model_dir), tmp_path)

    # Check that tokenizer works
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0

    # Check that model appeared in available list
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "my_model" in available  # directory name


def test_local_file_not_found(tmp_path):
    """Test error when local file not found."""
    nonexistent = tmp_path / "nonexistent.json"

    # Should attempt to download from HF Hub and fail
    with pytest.raises(RuntimeError, match="Failed to load tokenizer"):
        HFAdapter(str(nonexistent), tmp_path)


def test_local_directory_without_tokenizer_json(tmp_path):
    """Test error when tokenizer.json is missing in directory."""
    empty_dir = tmp_path / "empty_model"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="does not contain tokenizer.json"):
        HFAdapter(str(empty_dir), tmp_path)


def test_list_encoders_includes_hint(tmp_path):
    """Test that encoder list contains hint about local files."""
    encoders = HFAdapter.list_available_encoders(tmp_path)

    # Check for hint presence
    hints = [e for e in encoders if "local file" in e.lower()]
    assert len(hints) > 0
    assert any("tokenizer.json" in hint for hint in hints)


def test_local_model_persists_in_cache(simple_tokenizer_json, tmp_path):
    """Test that local model persists in cache after first load."""
    # Create temporary tokenizer.json file outside cache
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    tokenizer_file = external_dir / "custom_tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)

    # First load - imports to cache
    adapter1 = HFAdapter(str(tokenizer_file), tmp_path)
    text = "test"
    tokens1 = adapter1.count_tokens(text)

    # Check that model is in cache
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models" / "tokenizers" / "custom_tokenizer"
    assert cache_dir.exists()
    assert (cache_dir / "tokenizer.json").exists()

    # Delete original file
    tokenizer_file.unlink()

    # Second load - should work from cache using short name
    adapter2 = HFAdapter("custom_tokenizer", tmp_path)
    tokens2 = adapter2.count_tokens(text)

    # Results should match
    assert tokens1 == tokens2

    # Model should be in available list
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "custom_tokenizer" in available


def test_reusing_imported_model_by_name(simple_tokenizer_json, tmp_path):
    """Test reusing imported model by short name."""
    # Import model from local file
    external_file = tmp_path / "external" / "my_special_tokenizer.json"
    external_file.parent.mkdir()
    with open(external_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)

    # First load with full path - imports to cache
    adapter1 = HFAdapter(str(external_file), tmp_path)

    # Check that model is available in list
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "my_special_tokenizer" in available

    # Second load by short name - should work
    adapter2 = HFAdapter("my_special_tokenizer", tmp_path)

    # Both should work the same
    text = "Hello world"
    assert adapter1.count_tokens(text) == adapter2.count_tokens(text)

"""
Tests for support of local SentencePiece model files.
"""

import pytest
import sentencepiece as spm

from lg.stats.tokenizers import SPAdapter


@pytest.fixture
def simple_sp_model(tmp_path):
    """Creates simple SentencePiece model for tests."""
    # Create larger corpus for successful training
    text_file = tmp_path / "train.txt"
    # Generate diverse text
    corpus = []
    for i in range(1000):
        corpus.append(f"This is sentence number {i} with some words and tokens.")
        corpus.append(f"Python code example: def function_{i}():")
        corpus.append(f"Data {i}: abc xyz {i*2} items")
    text_file.write_text("\n".join(corpus), encoding="utf-8")

    # Train model with smaller vocab_size
    model_prefix = tmp_path / "test_model"
    spm.SentencePieceTrainer.train(
        input=str(text_file),
        model_prefix=str(model_prefix),
        vocab_size=500,  # Increased for successful training
        model_type="unigram",  # unigram works better on small corpora
        character_coverage=1.0,
    )

    return model_prefix.with_suffix(".model")


def test_load_from_local_file(simple_sp_model, tmp_path):
    """Test loading SentencePiece model from local file."""
    # Load model from file
    adapter = SPAdapter(str(simple_sp_model), tmp_path)

    # Check that model works
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
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "test_model" in available  # filename without extension


def test_load_from_local_directory(simple_sp_model, tmp_path):
    """Test loading SentencePiece model from directory."""
    # Create directory and copy model
    model_dir = tmp_path / "my_sp_model"
    model_dir.mkdir()

    import shutil
    dest_model = model_dir / simple_sp_model.name
    shutil.copy2(simple_sp_model, dest_model)

    # Load model from directory
    adapter = SPAdapter(str(model_dir), tmp_path)

    # Check that model works
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0

    # Check that model appeared in available list
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "my_sp_model" in available  # directory name


def test_local_model_persists_in_cache(simple_sp_model, tmp_path):
    """Test that local model persists in cache after first load."""
    # First load - imports to cache
    adapter1 = SPAdapter(str(simple_sp_model), tmp_path)
    text = "test"
    tokens1 = adapter1.count_tokens(text)

    # Check that model is in cache
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models" / "sentencepiece" / "test_model"
    assert cache_dir.exists()
    assert any(cache_dir.glob("*.model"))

    # Delete original file
    simple_sp_model.unlink()

    # Second load - should work from cache using short name
    adapter2 = SPAdapter("test_model", tmp_path)
    tokens2 = adapter2.count_tokens(text)

    # Results should match
    assert tokens1 == tokens2

    # Model should be in available list
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "test_model" in available


def test_reusing_imported_model_by_name(simple_sp_model, tmp_path):
    """Test reusing imported model by short name."""
    # Rename model for test
    import shutil
    renamed_model = simple_sp_model.parent / "my_custom_model.model"
    shutil.move(str(simple_sp_model), str(renamed_model))

    # First load with full path - imports to cache
    adapter1 = SPAdapter(str(renamed_model), tmp_path)

    # Check that model is available in list
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "my_custom_model" in available

    # Second load by short name - should work
    adapter2 = SPAdapter("my_custom_model", tmp_path)

    # Both should work the same
    text = "Hello world"
    assert adapter1.count_tokens(text) == adapter2.count_tokens(text)


def test_list_encoders_includes_hint(tmp_path):
    """Test that encoder list contains hint about local files."""
    encoders = SPAdapter.list_available_encoders(tmp_path)

    # Check for hint presence
    hints = [e for e in encoders if "local file" in e.lower()]
    assert len(hints) > 0
    assert any(".spm" in hint for hint in hints)

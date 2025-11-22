"""
Tests for lg.stats.tokenizers.model_cache.

Verify correct tokenization model caching:
- Cache structure creation
- Checking for models in cache
- List of cached models
- Safe conversion of model names with '/' to paths
"""

from pathlib import Path

import pytest

from lg.stats.tokenizers.model_cache import ModelCache


class TestModelCache:
    """Tests for basic ModelCache functionality."""

    def test_cache_initialization(self, tmp_path: Path):
        """Verifies cache structure creation on initialization."""
        cache = ModelCache(tmp_path)
        
        assert cache.cache_dir.exists()
        assert cache.cache_dir == tmp_path / ".lg-cache" / "tokenizer-models"
    
    def test_get_lib_cache_dir(self, tmp_path: Path):
        """Verifies directory creation for library."""
        cache = ModelCache(tmp_path)

        tokenizers_dir = cache.get_lib_cache_dir("tokenizers")
        assert tokenizers_dir.exists()
        assert tokenizers_dir == cache.cache_dir / "tokenizers"

        sp_dir = cache.get_lib_cache_dir("sentencepiece")
        assert sp_dir.exists()
        assert sp_dir == cache.cache_dir / "sentencepiece"

    def test_get_model_cache_dir_simple_name(self, tmp_path: Path):
        """Verifies directory creation for model with simple name."""
        cache = ModelCache(tmp_path)

        model_dir = cache.get_model_cache_dir("tokenizers", "gpt2")

        assert model_dir.exists()
        assert model_dir == cache.cache_dir / "tokenizers" / "gpt2"

    def test_get_model_cache_dir_with_slash(self, tmp_path: Path):
        """Verifies safe conversion of model names with '/'."""
        cache = ModelCache(tmp_path)

        model_dir = cache.get_model_cache_dir("sentencepiece", "t5-small")

        # For t5-small there are no slashes, path remains t5-small
        assert model_dir.exists()
        assert model_dir == cache.cache_dir / "sentencepiece" / "t5-small"

    def test_is_model_cached_tokenizers(self, tmp_path: Path):
        """Verifies checking for tokenizers model in cache."""
        cache = ModelCache(tmp_path)

        # Model is not cached
        assert not cache.is_model_cached("tokenizers", "gpt2")

        # Create model file
        model_dir = cache.get_model_cache_dir("tokenizers", "gpt2")
        (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")

        # Model is now in cache
        assert cache.is_model_cached("tokenizers", "gpt2")

    def test_is_model_cached_sentencepiece(self, tmp_path: Path):
        """Verifies checking for sentencepiece model in cache."""
        cache = ModelCache(tmp_path)

        # Model is not cached
        assert not cache.is_model_cached("sentencepiece", "t5-small")

        # Create model file
        model_dir = cache.get_model_cache_dir("sentencepiece", "t5-small")
        (model_dir / "tokenizer.model").write_bytes(b"fake model data")

        # Model is now in cache
        assert cache.is_model_cached("sentencepiece", "t5-small")

    def test_list_cached_models_empty(self, tmp_path: Path):
        """Verifies list of models in empty cache."""
        cache = ModelCache(tmp_path)

        assert cache.list_cached_models("tokenizers") == []
        assert cache.list_cached_models("sentencepiece") == []

    def test_list_cached_models_tokenizers(self, tmp_path: Path):
        """Verifies list of cached tokenizers models."""
        cache = ModelCache(tmp_path)

        # Create several models
        for model_name in ["gpt2", "roberta-base", "bert-base-uncased"]:
            model_dir = cache.get_model_cache_dir("tokenizers", model_name)
            (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")

        cached = cache.list_cached_models("tokenizers")

        assert len(cached) == 3
        assert "gpt2" in cached
        assert "roberta-base" in cached
        assert "bert-base-uncased" in cached

    def test_list_cached_models_sentencepiece(self, tmp_path: Path):
        """Verifies list of cached sentencepiece models."""
        cache = ModelCache(tmp_path)

        # Create several models (with / in name)
        models = ["t5-small", "meta-llama/Llama-2-7b-hf"]
        for model_name in models:
            model_dir = cache.get_model_cache_dir("sentencepiece", model_name)
            (model_dir / "tokenizer.model").write_bytes(b"fake model data")

        cached = cache.list_cached_models("sentencepiece")

        assert len(cached) == 2
        # Names should be restored with /
        assert "t5-small" in cached
        assert "meta-llama/Llama-2-7b-hf" in cached

    def test_list_cached_models_ignores_incomplete(self, tmp_path: Path):
        """Verifies that incomplete models (without required files) are ignored."""
        cache = ModelCache(tmp_path)

        # Create directory without model file
        incomplete_dir = cache.get_model_cache_dir("tokenizers", "incomplete-model")
        (incomplete_dir / "some-other-file.txt").write_text("not a tokenizer")

        # Create complete model
        complete_dir = cache.get_model_cache_dir("tokenizers", "gpt2")
        (complete_dir / "tokenizer.json").write_text("{}", encoding="utf-8")

        cached = cache.list_cached_models("tokenizers")

        # Only complete model in list
        assert len(cached) == 1
        assert "gpt2" in cached
        assert "incomplete-model" not in cached


class TestModelCacheIntegration:
    """Integration tests for cache with real adapters."""

    @pytest.mark.no_ci  # Requires pre-downloaded models for mock_hf_hub
    def test_tokenizers_adapter_uses_cache(self, tmp_path: Path, mock_hf_hub):
        """Verifies that HFAdapter uses cache on repeated requests."""
        from lg.stats.tokenizers.hf_adapter import HFAdapter

        # First load - should "download" model
        adapter1 = HFAdapter("gpt2", tmp_path)
        initial_downloads = mock_hf_hub.download_count

        # Second load - should use cache
        adapter2 = HFAdapter("gpt2", tmp_path)

        # Download count should not increase
        assert mock_hf_hub.download_count == initial_downloads

        # Both adapters should work
        text = "Hello, world!"
        tokens1 = adapter1.count_tokens(text)
        tokens2 = adapter2.count_tokens(text)

        assert tokens1 == tokens2
        assert tokens1 > 0

    @pytest.mark.no_ci  # Requires pre-downloaded models for mock_hf_hub
    def test_sentencepiece_adapter_uses_cache(self, tmp_path: Path, mock_hf_hub):
        """Verifies that SPAdapter uses cache on repeated requests."""
        from lg.stats.tokenizers.sp_adapter import SPAdapter

        # First load - should "download" model
        adapter1 = SPAdapter("t5-small", tmp_path)
        initial_downloads = mock_hf_hub.download_count

        # Second load - should use cache
        adapter2 = SPAdapter("t5-small", tmp_path)

        # Download count should not increase
        assert mock_hf_hub.download_count == initial_downloads

        # Both adapters should work
        text = "Hello, world!"
        tokens1 = adapter1.count_tokens(text)
        tokens2 = adapter2.count_tokens(text)

        assert tokens1 == tokens2
        assert tokens1 > 0

    @pytest.mark.no_ci  # Requires pre-downloaded models for mock_hf_hub
    def test_cache_persists_across_sessions(self, tmp_path: Path, mock_hf_hub):
        """Verifies that cache persists between 'sessions'."""
        from lg.stats.tokenizers.hf_adapter import HFAdapter
        from lg.stats.tokenizers.model_cache import ModelCache

        # First "session" - load model
        adapter1 = HFAdapter("gpt2", tmp_path)
        download_count_after_first = mock_hf_hub.download_count

        # Check that model is in cache
        cache = ModelCache(tmp_path)
        assert cache.is_model_cached("tokenizers", "gpt2")

        # Second "session" - create new adapter
        # (simulate program restart)
        adapter2 = HFAdapter("gpt2", tmp_path)

        # Model should not be downloaded again
        assert mock_hf_hub.download_count == download_count_after_first

        # Adapter should work
        text = "Test text"
        assert adapter2.count_tokens(text) > 0

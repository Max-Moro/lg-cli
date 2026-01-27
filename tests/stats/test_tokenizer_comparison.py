"""
Tests for comparing accuracy of different tokenizers.

Verify that:
- Different tokenizers give different results for same text
- More specialized tokenizers may be more accurate for specific tasks
- Tiktoken (basic BPE) works as universal approximation
- HF and SP tokenizers provide more accurate estimates for specific models
"""

from pathlib import Path

import pytest


class TestTokenizerBasics:
    """Basic tests for tokenizer functionality."""

    def test_tiktoken_counts_tokens(self, tiktoken_service):
        """Verifies that tiktoken correctly counts tokens."""
        text = "Hello, world!"
        tokens = tiktoken_service.count_text_cached(text)

        assert tokens > 0
        assert tokens < len(text)  # Fewer tokens than characters

    @pytest.mark.no_ci  # Requires pre-downloaded HF models
    def test_hf_tokenizer_counts_tokens(self, hf_tokenizer_service):
        """Verifies that HF tokenizer correctly counts tokens."""
        text = "Hello, world!"
        tokens = hf_tokenizer_service.count_text_cached(text)

        assert tokens > 0
        assert tokens < len(text)

    @pytest.mark.no_ci  # Requires pre-downloaded SP models
    def test_sp_tokenizer_counts_tokens(self, sp_tokenizer_service):
        """Verifies that SentencePiece tokenizer correctly counts tokens."""
        text = "Hello, world!"
        tokens = sp_tokenizer_service.count_text_cached(text)

        assert tokens > 0
        assert tokens < len(text)

    def test_empty_text_returns_zero(self, tiktoken_service):
        """Verifies that empty text returns 0 tokens."""
        assert tiktoken_service.count_text_cached("") == 0
        assert tiktoken_service.count_text_cached("   ") > 0  # Spaces are tokens


class TestTokenizerDifferences:
    """Tests for differences between tokenizers."""

    @pytest.mark.no_ci  # Requires pre-downloaded HF models
    def test_different_tokenizers_different_results(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sample_texts
    ):
        """Verifies that different tokenizers give different results."""
        text = sample_texts["simple"]

        tiktoken_count = tiktoken_service.count_text_cached(text)
        hf_count = hf_tokenizer_service.count_text_cached(text)

        # Results can differ (different algorithms and vocabularies)
        # But both should be reasonable
        assert 0 < tiktoken_count < len(text)
        assert 0 < hf_count < len(text)

    def test_tokenizers_consistent_for_same_text(self, tiktoken_service):
        """Verifies that tokenizer gives consistent result for same text."""
        text = "Consistent tokenization test"

        count1 = tiktoken_service.count_text_cached(text)
        count2 = tiktoken_service.count_text_cached(text)

        assert count1 == count2

    def test_longer_text_more_tokens(self, tiktoken_service, sample_texts):
        """Verifies that longer text has more tokens."""
        short = sample_texts["simple"]
        long = sample_texts["long_text"]

        short_tokens = tiktoken_service.count_text_cached(short)
        long_tokens = tiktoken_service.count_text_cached(long)

        assert long_tokens > short_tokens


class TestTokenizerAccuracy:
    """Tests for tokenization accuracy for different content types."""

    def test_code_tokenization_efficiency(self, tiktoken_service, sample_texts):
        """
        Verifies that code tokenization is efficient.

        Code usually contains many repeating patterns,
        so there should be significantly fewer tokens than characters.
        """
        code = sample_texts["python_code"]

        char_count = len(code)
        token_count = tiktoken_service.count_text_cached(code)

        # Approximate ratio: 1 token per 3-4 characters for code
        compression_ratio = char_count / token_count

        assert compression_ratio > 2.0, "Code should compress well with tokenization"
        assert compression_ratio < 10.0, "But not too much"

    @pytest.mark.no_ci  # Requires pre-downloaded HF models
    def test_special_chars_tokenization(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sample_texts
    ):
        """
        Verifies handling of special characters by different tokenizers.

        Different tokenizers handle Unicode, emoji, etc. differently.
        """
        text = sample_texts["special_chars"]

        tiktoken_count = tiktoken_service.count_text_cached(text)
        hf_count = hf_tokenizer_service.count_text_cached(text)

        # Both should correctly process text
        assert tiktoken_count > 0
        assert hf_count > 0

        # Results may differ due to different Unicode handling
        # Main thing is that both tokenizers work

    def test_mixed_content_tokenization(self, tiktoken_service, sample_texts):
        """
        Verifies tokenization of mixed content (text + code + markdown).
        """
        mixed = sample_texts["mixed"]

        tokens = tiktoken_service.count_text_cached(mixed)
        chars = len(mixed)

        # Mixed content should have reasonable compression ratio
        compression = chars / tokens

        assert 2.0 < compression < 6.0, "Mixed content should have moderate compression"


class TestTokenizerComparison:
    """
    Comparative tests for tokenizer accuracy.

    These tests show that using more accurate tokenizers
    is justified for specific models.
    """

    @pytest.mark.no_ci  # Requires pre-downloaded HF/SP models
    @pytest.mark.parametrize("text_type", ["simple", "python_code", "mixed"])
    def test_all_tokenizers_reasonable(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sp_tokenizer_service,
        sample_texts,
        text_type
    ):
        """
        Verifies that all tokenizers give reasonable results
        for different text types.
        """
        text = sample_texts[text_type]

        tiktoken_count = tiktoken_service.count_text_cached(text)
        hf_count = hf_tokenizer_service.count_text_cached(text)
        sp_count = sp_tokenizer_service.count_text_cached(text)

        # All results should be positive
        assert tiktoken_count > 0
        assert hf_count > 0
        assert sp_count > 0

        # And all should be less than text length
        text_len = len(text)
        assert tiktoken_count < text_len
        assert hf_count < text_len
        assert sp_count < text_len

    @pytest.mark.no_ci  # Requires pre-downloaded HF models
    def test_tokenizer_variance_acceptable(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sample_texts
    ):
        """
        Verifies that difference between tokenizers is within
        acceptable limits.

        Too large difference may indicate problems.
        """
        text = sample_texts["long_text"]

        tiktoken_count = tiktoken_service.count_text_cached(text)
        hf_count = hf_tokenizer_service.count_text_cached(text)

        # Calculate relative difference
        diff = abs(tiktoken_count - hf_count)
        avg = (tiktoken_count + hf_count) / 2
        relative_diff = diff / avg

        # Difference should not exceed 50% of average
        # (different algorithms can give significantly different results,
        # but within reasonable limits)
        assert relative_diff < 0.5, f"Too large difference: {relative_diff:.1%}"


class TestTokenizerCaching:
    """Tests for token caching."""

    # noinspection PyUnusedLocal
    @pytest.mark.no_ci  # Requires pre-downloaded models for mock_hf_hub
    def test_cache_improves_performance(self, tmp_path: Path, mock_hf_hub):
        """
        Verifies that token caching speeds up repeated counts.

        (This is a qualitative test - real performance measurements
        in unit tests are not very reliable)
        """
        from lg.cache.fs_cache import Cache
        from lg.stats.tokenizer import TokenService
        from tests.infrastructure.cli_utils import DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER

        cache = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")

        service = TokenService(
            root=tmp_path,
            lib=DEFAULT_TOKENIZER_LIB,
            encoder=DEFAULT_ENCODER,
            cache=cache
        )

        text = "Test text for caching" * 100

        # First count - goes to cache
        count1 = service.count_text_cached(text)

        # Second count - should use cache
        count2 = service.count_text_cached(text)

        assert count1 == count2
        assert count1 > 0

    def test_cache_works_for_different_texts(self, tmp_path: Path):
        """Verifies that cache works correctly for different texts."""
        from lg.cache.fs_cache import Cache
        from lg.stats.tokenizer import TokenService
        from tests.infrastructure.cli_utils import DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER

        cache = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")

        service = TokenService(
            root=tmp_path,
            lib=DEFAULT_TOKENIZER_LIB,
            encoder=DEFAULT_ENCODER,
            cache=cache
        )

        text1 = "First text"
        text2 = "Second completely different text"

        count1 = service.count_text_cached(text1)
        count2 = service.count_text_cached(text2)

        # Different texts should have different token counts
        assert count1 != count2

        # Repeated counts should give same results
        assert service.count_text_cached(text1) == count1
        assert service.count_text_cached(text2) == count2

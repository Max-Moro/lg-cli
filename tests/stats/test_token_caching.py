"""
Tests for token counting caching system.

Architecture overview:
- TokenService provides two-level caching for token counting:
  - L1 (memory): LRU cache using OrderedDict, up to MEMORY_CACHE_SIZE entries
  - L2 (file): Persistent cache via Cache class for large strings (≥200 chars)

- Cache class provides file-based token storage:
  - get_text_tokens(text, cache_key) -> Optional[int]
  - put_text_tokens(text, model, token_count) -> None
  - Uses SHA1 hash of text as key, stores counts per model

Key thresholds:
- SMALL_TEXT_THRESHOLD = 200 chars (below this, only L1 is used)
- MEMORY_CACHE_SIZE = 10000 entries (LRU eviction threshold)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.stats.tokenizer import TokenService, SMALL_TEXT_THRESHOLD, MEMORY_CACHE_SIZE
from tests.infrastructure import DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    """Creates an enabled file cache in temporary directory."""
    return Cache(tmp_path, enabled=True, fresh=False, tool_version="test")


@pytest.fixture
def disabled_cache(tmp_path: Path) -> Cache:
    """Creates a disabled file cache."""
    return Cache(tmp_path, enabled=False, fresh=False, tool_version="test")


@pytest.fixture
def token_service(tmp_path: Path, cache: Cache) -> TokenService:
    """Creates TokenService with L2 cache enabled."""
    return TokenService(
        root=tmp_path,
        lib=DEFAULT_TOKENIZER_LIB,
        encoder=DEFAULT_ENCODER,
        cache=cache
    )


@pytest.fixture
def token_service_no_cache(tmp_path: Path) -> TokenService:
    """Creates TokenService without L2 cache (L1 only)."""
    return TokenService(
        root=tmp_path,
        lib=DEFAULT_TOKENIZER_LIB,
        encoder=DEFAULT_ENCODER,
        cache=None
    )


@pytest.fixture
def small_text() -> str:
    """Text below SMALL_TEXT_THRESHOLD (L1 only)."""
    text = "Hello, world! This is a small text."
    assert len(text) < SMALL_TEXT_THRESHOLD
    return text


@pytest.fixture
def large_text() -> str:
    """Text at or above SMALL_TEXT_THRESHOLD (L1 + L2)."""
    text = "This is a larger text that exceeds the threshold. " * 10
    assert len(text) >= SMALL_TEXT_THRESHOLD
    return text


# ============================================================================
# L1 Memory Cache Tests
# ============================================================================

class TestL1MemoryCache:
    """Tests for in-memory LRU cache (L1)."""

    def test_empty_text_returns_zero(self, token_service: TokenService):
        """Empty text should return 0 without caching."""
        assert token_service.count_text_cached("") == 0
        assert token_service.count_text_cached("   ") > 0  # Whitespace counts

    def test_same_text_uses_cache(self, token_service_no_cache: TokenService, small_text: str):
        """Repeated calls for same text should use L1 cache."""
        # Track actual tokenizer calls
        call_count = 0
        original_count = token_service_no_cache._tokenizer.count_tokens

        def counting_wrapper(text: str) -> int:
            nonlocal call_count
            call_count += 1
            return original_count(text)

        token_service_no_cache._tokenizer.count_tokens = counting_wrapper

        # First call - should tokenize
        result1 = token_service_no_cache.count_text_cached(small_text)
        assert call_count == 1

        # Second call - should use cache
        result2 = token_service_no_cache.count_text_cached(small_text)
        assert call_count == 1  # No new tokenization
        assert result1 == result2

        # Third call - still cached
        result3 = token_service_no_cache.count_text_cached(small_text)
        assert call_count == 1
        assert result1 == result3

    def test_different_texts_tokenized_separately(self, token_service_no_cache: TokenService):
        """Different texts should be tokenized and cached separately."""
        text1 = "First text"
        text2 = "Second different text"

        count1 = token_service_no_cache.count_text_cached(text1)
        count2 = token_service_no_cache.count_text_cached(text2)

        assert count1 != count2
        assert count1 > 0
        assert count2 > 0

    def test_l1_cache_is_instance_isolated(self, tmp_path: Path):
        """Each TokenService instance has its own L1 cache."""
        text = "Shared text for testing"

        service1 = TokenService(
            root=tmp_path, lib=DEFAULT_TOKENIZER_LIB,
            encoder=DEFAULT_ENCODER, cache=None
        )
        service2 = TokenService(
            root=tmp_path, lib=DEFAULT_TOKENIZER_LIB,
            encoder=DEFAULT_ENCODER, cache=None
        )

        # Both should tokenize (separate L1 caches)
        call_count = {"s1": 0, "s2": 0}
        orig1 = service1._tokenizer.count_tokens
        orig2 = service2._tokenizer.count_tokens

        service1._tokenizer.count_tokens = lambda t: (call_count.__setitem__("s1", call_count["s1"] + 1), orig1(t))[1]
        service2._tokenizer.count_tokens = lambda t: (call_count.__setitem__("s2", call_count["s2"] + 1), orig2(t))[1]

        service1.count_text_cached(text)
        service2.count_text_cached(text)

        assert call_count["s1"] == 1
        assert call_count["s2"] == 1

    def test_lru_eviction(self, token_service_no_cache: TokenService):
        """LRU eviction should work when cache exceeds MEMORY_CACHE_SIZE."""
        # Fill cache beyond limit
        for i in range(MEMORY_CACHE_SIZE + 100):
            token_service_no_cache.count_text_cached(f"text_{i}")

        # Cache should not exceed limit
        assert len(token_service_no_cache._memory_cache) <= MEMORY_CACHE_SIZE


# ============================================================================
# L2 File Cache Tests (Cache class)
# ============================================================================

class TestL2FileCache:
    """Tests for file-based persistent cache (L2)."""

    def test_get_returns_none_for_missing(self, cache: Cache):
        """get_text_tokens returns None for uncached text."""
        result = cache.get_text_tokens("never seen text", "tiktoken:cl100k_base")
        assert result is None

    def test_put_and_get_roundtrip(self, cache: Cache):
        """put_text_tokens followed by get_text_tokens returns correct value."""
        text = "Test text for caching"
        cache_key = "tiktoken:cl100k_base"
        token_count = 42

        cache.put_text_tokens(text, cache_key, token_count)
        result = cache.get_text_tokens(text, cache_key)

        assert result == token_count

    def test_different_models_stored_separately(self, cache: Cache):
        """Same text with different models should have independent counts."""
        text = "Same text, different models"
        key1 = "tiktoken:cl100k_base"
        key2 = "tiktoken:p50k_base"

        cache.put_text_tokens(text, key1, 100)
        cache.put_text_tokens(text, key2, 150)

        assert cache.get_text_tokens(text, key1) == 100
        assert cache.get_text_tokens(text, key2) == 150

    def test_disabled_cache_returns_none(self, disabled_cache: Cache):
        """Disabled cache should always return None."""
        text = "Test text"
        cache_key = "tiktoken:cl100k_base"

        disabled_cache.put_text_tokens(text, cache_key, 42)
        result = disabled_cache.get_text_tokens(text, cache_key)

        assert result is None

    def test_empty_text_not_cached(self, cache: Cache):
        """Empty text should not be cached."""
        cache.put_text_tokens("", "tiktoken:cl100k_base", 0)
        assert cache.get_text_tokens("", "tiktoken:cl100k_base") is None

    def test_cache_persists_across_instances(self, tmp_path: Path):
        """Cache should persist data between Cache instances."""
        text = "Persistent text"
        cache_key = "tiktoken:cl100k_base"
        token_count = 77

        # First cache instance - write
        cache1 = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")
        cache1.put_text_tokens(text, cache_key, token_count)

        # Second cache instance - read
        cache2 = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")
        result = cache2.get_text_tokens(text, cache_key)

        assert result == token_count


# ============================================================================
# TokenService + Cache Integration Tests
# ============================================================================

class TestTokenServiceCacheIntegration:
    """Integration tests for TokenService with L2 cache."""

    def test_small_text_uses_l1_only(self, token_service: TokenService, small_text: str):
        """Text below threshold should only use L1, not L2."""
        assert len(small_text) < SMALL_TEXT_THRESHOLD

        # First call
        result = token_service.count_text_cached(small_text)
        assert result > 0

        # L2 cache should NOT have this text
        cache_key = f"{token_service.lib}:{token_service.encoder}"
        assert token_service.cache.get_text_tokens(small_text, cache_key) is None

    def test_large_text_uses_both_caches(self, token_service: TokenService, large_text: str):
        """Text at/above threshold should use both L1 and L2."""
        assert len(large_text) >= SMALL_TEXT_THRESHOLD

        # First call
        result = token_service.count_text_cached(large_text)
        assert result > 0

        # L2 cache SHOULD have this text
        cache_key = f"{token_service.lib}:{token_service.encoder}"
        cached = token_service.cache.get_text_tokens(large_text, cache_key)
        assert cached == result

    def test_l2_cache_prevents_retokenization(self, tmp_path: Path, cache: Cache, large_text: str):
        """L2 cache should prevent tokenization across TokenService instances."""
        call_count = 0

        def make_counting_service():
            nonlocal call_count
            service = TokenService(
                root=tmp_path,
                lib=DEFAULT_TOKENIZER_LIB,
                encoder=DEFAULT_ENCODER,
                cache=cache
            )
            orig = service._tokenizer.count_tokens

            def wrapper(t):
                nonlocal call_count
                call_count += 1
                return orig(t)

            service._tokenizer.count_tokens = wrapper
            return service

        # First service - should tokenize
        service1 = make_counting_service()
        result1 = service1.count_text_cached(large_text)
        assert call_count == 1

        # Second service with same cache - should use L2, no tokenization
        service2 = make_counting_service()
        result2 = service2.count_text_cached(large_text)
        assert call_count == 1  # No new tokenization!
        assert result1 == result2

    def test_l1_populated_from_l2(self, tmp_path: Path, large_text: str):
        """When L2 cache hits, L1 should also be populated."""
        cache = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")
        cache_key = f"{DEFAULT_TOKENIZER_LIB}:{DEFAULT_ENCODER}"

        # Pre-populate L2 cache
        cache.put_text_tokens(large_text, cache_key, 999)

        # Create service and query
        service = TokenService(
            root=tmp_path,
            lib=DEFAULT_TOKENIZER_LIB,
            encoder=DEFAULT_ENCODER,
            cache=cache
        )

        # Should get from L2 and populate L1
        result = service.count_text_cached(large_text)
        assert result == 999

        # Verify L1 is populated
        assert service._get_from_memory_cache(large_text) == 999


# ============================================================================
# TokenService Helper Methods Tests
# ============================================================================

class TestTokenServiceHelpers:
    """Tests for TokenService utility methods."""

    def test_compare_texts(self, token_service: TokenService):
        """compare_texts should return correct comparison metrics."""
        original = "This is a longer original text with more content."
        replacement = "Short."

        orig_tokens, repl_tokens, savings, ratio = token_service.compare_texts(original, replacement)

        assert orig_tokens > repl_tokens
        assert savings == orig_tokens - repl_tokens
        assert savings > 0
        assert ratio == savings / repl_tokens

    def test_compare_texts_no_savings(self, token_service: TokenService):
        """compare_texts with longer replacement should show zero savings."""
        original = "Short"
        replacement = "This is a much longer replacement text"

        orig_tokens, repl_tokens, savings, ratio = token_service.compare_texts(original, replacement)

        assert orig_tokens < repl_tokens
        assert savings == 0  # max(0, negative) = 0

    def test_is_economical_true(self, token_service: TokenService):
        """is_economical should return True when ratio exceeds threshold."""
        original = "This is a very long original text that will be significantly compressed."
        replacement = "Short"

        result = token_service.is_economical(
            original, replacement,
            min_ratio=0.5,
            min_abs_savings_if_none=0
        )
        assert result is True

    def test_is_economical_false(self, token_service: TokenService):
        """is_economical should return False when ratio is below threshold."""
        original = "Short"
        replacement = "Also short"

        result = token_service.is_economical(
            original, replacement,
            min_ratio=0.5,
            min_abs_savings_if_none=0
        )
        assert result is False

    def test_is_economical_empty_replacement_threshold(self, token_service: TokenService):
        """is_economical with empty replacement should check min_abs_savings."""
        original = "Tiny"  # Very few tokens

        # Should fail: savings < min_abs_savings_if_none
        result = token_service.is_economical(
            original, "",
            min_ratio=0.0,
            min_abs_savings_if_none=100
        )
        assert result is False

    def test_truncate_to_tokens_no_truncation(self, token_service: TokenService):
        """truncate_to_tokens should return original if within limit."""
        text = "Short text"
        tokens = token_service.count_text_cached(text)

        result = token_service.truncate_to_tokens(text, tokens + 10)
        assert result == text

    def test_truncate_to_tokens_truncates(self, token_service: TokenService):
        """truncate_to_tokens should truncate when over limit."""
        text = "This is a longer text that should definitely be truncated to fit the limit"
        max_tokens = 5

        result = token_service.truncate_to_tokens(text, max_tokens)

        assert len(result) < len(text)
        # Result should be roughly proportional
        result_tokens = token_service.count_text_cached(result)
        # Due to proportional estimation, might be slightly off
        assert result_tokens <= max_tokens + 2

    def test_truncate_empty_text(self, token_service: TokenService):
        """truncate_to_tokens should handle empty text."""
        assert token_service.truncate_to_tokens("", 100) == ""


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Edge cases and error handling tests."""

    def test_unicode_text_caching(self, token_service: TokenService):
        """Unicode text should be cached correctly."""
        text = "Привет мир! 你好世界! 🎉🚀"

        count1 = token_service.count_text_cached(text)
        count2 = token_service.count_text_cached(text)

        assert count1 == count2
        assert count1 > 0

    def test_very_long_text(self, token_service: TokenService):
        """Very long text should work with caching."""
        text = "word " * 10000  # ~50k chars

        count1 = token_service.count_text_cached(text)
        count2 = token_service.count_text_cached(text)

        assert count1 == count2
        assert count1 > 0

    def test_whitespace_variations(self, token_service: TokenService):
        """Different whitespace should produce different counts."""
        text1 = "hello world"
        text2 = "hello  world"
        text3 = "hello\nworld"

        count1 = token_service.count_text_cached(text1)
        count2 = token_service.count_text_cached(text2)
        count3 = token_service.count_text_cached(text3)

        # At least some should differ
        assert not (count1 == count2 == count3)

    def test_cache_key_includes_encoder(self, tmp_path: Path, cache: Cache, large_text: str):
        """Different encoders should have separate cache entries."""
        service1 = TokenService(
            root=tmp_path, lib="tiktoken", encoder="cl100k_base", cache=cache
        )
        service2 = TokenService(
            root=tmp_path, lib="tiktoken", encoder="p50k_base", cache=cache
        )

        count1 = service1.count_text_cached(large_text)
        count2 = service2.count_text_cached(large_text)

        # Both should be cached with different keys
        assert cache.get_text_tokens(large_text, "tiktoken:cl100k_base") == count1
        assert cache.get_text_tokens(large_text, "tiktoken:p50k_base") == count2

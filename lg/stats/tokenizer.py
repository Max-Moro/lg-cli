from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Tuple

from .tokenizers import BaseTokenizer, create_tokenizer

"""
Token counting service.

Created once at the start of the pipeline and provides
a unified API for working with different tokenizers.
"""

# Heuristics for two-level cache
SMALL_TEXT_THRESHOLD = 200  # chars - use only in-memory cache
MEMORY_CACHE_SIZE = 10000   # max entries in LRU cache (~1-2 MB)


class TokenService:
    """
    Wrapper around BaseTokenizer with two-level caching:
    - L1 (memory): Fast LRU cache for small strings and hot data
    - L2 (file): Persistent cache for large strings across runs
    """

    def __init__(
        self,
        root: Path,
        lib: str,
        encoder: str,
        *,
        cache=None
    ):
        """
        Args:
            root: Project root
            lib: Library name (tiktoken, tokenizers, sentencepiece)
            encoder: Encoder/model name
            cache: File cache for tokens (optional)
        """
        self.root = root
        self.lib = lib
        self.encoder = encoder
        self.cache = cache

        # Create tokenizer
        self._tokenizer = create_tokenizer(lib, encoder, root)

        # L1 cache: in-memory LRU for fast access
        self._memory_cache: OrderedDict[str, int] = OrderedDict()

    @property
    def tokenizer(self) -> BaseTokenizer:
        """Return the base tokenizer."""
        return self._tokenizer

    @property
    def encoder_name(self) -> str:
        """Encoder name."""
        return self.encoder

    def count_text(self, text: str) -> int:
        """Count tokens in text."""
        return self._tokenizer.count_tokens(text)

    def _get_from_memory_cache(self, text: str) -> int | None:
        """Get token count from in-memory LRU cache."""
        if text in self._memory_cache:
            # Move to end (mark as recently used)
            self._memory_cache.move_to_end(text)
            return self._memory_cache[text]
        return None

    def _put_to_memory_cache(self, text: str, count: int) -> None:
        """Put token count to in-memory LRU cache."""
        # Add to cache
        self._memory_cache[text] = count
        self._memory_cache.move_to_end(text)

        # Evict oldest if over limit
        while len(self._memory_cache) > MEMORY_CACHE_SIZE:
            self._memory_cache.popitem(last=False)

    def count_text_cached(self, text: str) -> int:
        """
        Count tokens in text using two-level cache:
        - Small strings (<200 chars): L1 (memory) only - fast, no disk I/O
        - Large strings (>=200 chars): L1 (memory) + L2 (file) - persistence

        This avoids expensive file operations for high-frequency small string access.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        # Check L1 (memory) cache first for all strings
        cached = self._get_from_memory_cache(text)
        if cached is not None:
            return cached

        # For small strings, skip file cache (avoid disk I/O overhead)
        is_small = len(text) < SMALL_TEXT_THRESHOLD

        if is_small or not self.cache:
            # Count directly and cache in memory only
            token_count = self.count_text(text)
            self._put_to_memory_cache(text, token_count)
            return token_count

        # For large strings, check L2 (file) cache
        cache_key = f"{self.lib}:{self.encoder}"
        cached_tokens = self.cache.get_text_tokens(text, cache_key)
        if cached_tokens is not None:
            # Found in file cache - add to memory cache too
            self._put_to_memory_cache(text, cached_tokens)
            return cached_tokens

        # Not in any cache - count and save to both levels
        token_count = self.count_text(text)
        self._put_to_memory_cache(text, token_count)
        self.cache.put_text_tokens(text, cache_key, token_count)

        return token_count

    def compare_texts(self, original: str, replacement: str) -> Tuple[int, int, int, float]:
        """
        Compare cost of original and replacement.

        Returns: (orig_tokens, repl_tokens, savings, ratio)
        ratio = savings / max(repl_tokens, 1)
        """
        orig = self.count_text(original)
        repl = self.count_text(replacement)
        savings = max(0, orig - repl)
        ratio = savings / float(max(repl, 1))
        return orig, repl, savings, ratio

    def is_economical(self, original: str, replacement: str, *, min_ratio: float, replacement_is_none: bool,
                       min_abs_savings_if_none: int) -> bool:
        """
        Check if replacement is economical.

        - For regular placeholders, only the threshold savings/replacement ≥ min_ratio is applied.
        - For "empty" replacements (replacement_is_none=True), an absolute token savings threshold
          (min_abs_savings_if_none) can additionally be applied to avoid microscopic deletions.
        """
        orig, repl, savings, ratio = self.compare_texts(original, replacement)

        if replacement_is_none and savings < min_abs_savings_if_none:
            return False

        return ratio >= float(min_ratio)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to a specified number of tokens using proportional ratio.

        Args:
            text: Original text to truncate
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text that fits within the specified token limit
        """
        if not text:
            return ""

        current_tokens = self.count_text(text)
        if current_tokens <= max_tokens:
            return text

        # Proportional truncation by character count
        ratio = max_tokens / current_tokens
        target_length = int(len(text) * ratio)

        # Truncate to target length, but not less than 1 character
        target_length = max(1, target_length)
        trimmed = text[:target_length].rstrip()

        return trimmed

def default_tokenizer() -> TokenService:
    """Quick creation of tokenization service (for tests)."""
    return TokenService(
        root=None,
        lib="tiktoken",
        encoder="cl100k_base"
    )
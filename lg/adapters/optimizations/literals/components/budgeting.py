"""
Token budget calculations for literal optimization.

Provides utilities for calculating token overhead and managing
budget-related computations for literal structure processing.
"""

from lg.stats.tokenizer import TokenService


class BudgetCalculator:
    """
    Calculates token overhead for literal structures.

    Handles budget-aware calculations for literal delimiters,
    placeholders, and formatting overhead.
    """

    def __init__(self, tokenizer: TokenService):
        """
        Initialize calculator with tokenizer.

        Args:
            tokenizer: Token counting service
        """
        self.tokenizer = tokenizer

    def calculate_overhead(
        self,
        opening: str,
        closing: str,
        placeholder: str,
        is_multiline: bool = False,
        indent: str = "",
    ) -> int:
        """
        Calculate token overhead for literal structure.

        Computes the token cost of the literal's structural elements:
        opening delimiter, placeholder, and closing delimiter.
        For multiline literals, includes newlines and indentation.

        Args:
            opening: Opening delimiter (e.g., "[", "{")
            closing: Closing delimiter (e.g., "]", "}")
            placeholder: Placeholder text (e.g., "...", "more items")
            is_multiline: Whether literal is multiline formatted
            indent: Indentation string for multiline formatting

        Returns:
            Total overhead tokens
        """
        overhead_text = f"{opening}{placeholder}{closing}"
        if is_multiline:
            overhead_text = f"{opening}\n{indent}{placeholder}\n{indent}{closing}"

        return self.tokenizer.count_text_cached(overhead_text)

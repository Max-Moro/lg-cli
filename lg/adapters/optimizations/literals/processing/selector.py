"""
Budget-aware element selection for literal trimming.

Implements algorithms for selecting which elements to keep
within a token budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from lg.stats.tokenizer import TokenService
from ..utils.element_parser import Element, ElementParser


@dataclass
class SelectionBase:
    """
    Base class for element selection results.

    Contains common fields shared by all selection types.
    """
    # Elements to keep in output
    kept_elements: List[Element]

    # Elements that were removed
    removed_elements: List[Element]

    # Total elements in original
    total_count: int

    # Token accounting
    tokens_kept: int
    tokens_removed: int

    @property
    def kept_count(self) -> int:
        return len(self.kept_elements)

    @property
    def removed_count(self) -> int:
        return len(self.removed_elements)

    @property
    def has_removals(self) -> bool:
        return self.removed_count > 0

    @property
    def total_tokens_saved(self) -> int:
        """
        Total tokens removed by this selection.

        Returns:
            Total number of tokens removed
        """
        return self.tokens_removed


@dataclass
class Selection(SelectionBase):
    """
    Result of budget-aware element selection.

    Contains information about which elements were kept,
    which were removed, and where to place placeholder.
    """
    # Suggested placeholder position (index in kept_elements, or -1 for end)
    placeholder_index: int = -1


class BudgetSelector:
    """
    Selects elements that fit within a token budget.

    Strategies:
    - FIRST: Keep first N elements that fit
    - FIRST_LAST: Keep first and last elements
    - DISTRIBUTE: Keep elements distributed across the list
    """

    def __init__(self, tokenizer: TokenService):
        """Initialize selector with tokenizer."""
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

        Args:
            opening: Opening delimiter
            closing: Closing delimiter
            placeholder: Placeholder text
            is_multiline: Whether literal is multiline
            indent: Indentation string

        Returns:
            Total overhead tokens
        """
        overhead_text = f"{opening}{placeholder}{closing}"
        if is_multiline:
            overhead_text = f"{opening}\n{indent}{placeholder}\n{indent}{closing}"

        return self.tokenizer.count_text_cached(overhead_text)

    def select(
        self,
        elements: List[Element],
        budget: int,
        parser: ElementParser,
        min_keep: int = 1,
        tuple_size: int = 1,
        preserve_top_level_keys: bool = False,
    ) -> Selection:
        """
        Select elements using simple budget-aware strategy.

        No DFS - pipeline handles nesting via inside-out processing.

        Args:
            elements: List of elements at current level
            budget: Token budget
            parser: ElementParser (unused, kept for compatibility)
            min_keep: Minimum elements to keep
            tuple_size: Group elements into tuples
            preserve_top_level_keys: Keep all keys (for typed structs)

        Returns:
            Selection with kept/removed elements
        """

        if not elements:
            return Selection(
                kept_elements=[],
                removed_elements=[],
                total_count=0,
                tokens_kept=0,
                tokens_removed=0,
            )

        # Group elements into tuples if needed
        if tuple_size > 1:
            groups = [elements[i:i + tuple_size] for i in range(0, len(elements), tuple_size)]
        else:
            groups = [[e] for e in elements]

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0
        groups_kept = 0

        for group in groups:
            # Calculate group tokens (simple, no nested optimization)
            group_tokens = sum(self.tokenizer.count_text_cached(e.text) for e in group)

            # Determine if we must keep this group
            must_keep = groups_kept < min_keep
            must_preserve = preserve_top_level_keys  # For typed structs

            if group_tokens <= budget - tokens_used or must_keep or must_preserve:
                # Keep this group
                kept.extend(group)
                tokens_used += group_tokens
                groups_kept += 1
            else:
                # Budget exhausted
                # Add this group and all remaining to removed
                for remaining_group in groups[groups_kept:]:
                    removed.extend(remaining_group)
                break

        # Calculate tokens removed
        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed
        )

        total_count = len(groups) if tuple_size > 1 else len(elements)

        return Selection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=total_count,
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
        )

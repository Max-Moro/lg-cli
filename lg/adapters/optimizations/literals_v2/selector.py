"""
Budget-aware element selection for literal trimming.

Implements algorithms for selecting which elements to keep
within a token budget, including DFS selection for nested structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, TYPE_CHECKING

from .parser import Element, ElementParser, ParseConfig
from lg.stats.tokenizer import TokenService

if TYPE_CHECKING:
    from .parser import Element


@dataclass
class Selection:
    """
    Result of budget-aware element selection.

    Contains information about which elements were kept,
    which were removed, and where to place placeholder.
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

    # Suggested placeholder position (index in kept_elements, or -1 for end)
    placeholder_index: int = -1

    @property
    def kept_count(self) -> int:
        return len(self.kept_elements)

    @property
    def removed_count(self) -> int:
        return len(self.removed_elements)

    @property
    def has_removals(self) -> bool:
        return self.removed_count > 0


@dataclass
class DFSSelection:
    """
    Result of DFS (depth-first) element selection for nested structures.

    Extends Selection with recursive nested selections.
    """
    # Elements to keep at this level
    kept_elements: List[Element]

    # Elements that were removed at this level
    removed_elements: List[Element]

    # Total elements at this level
    total_count: int

    # Token accounting for this level (not including nested)
    tokens_kept: int
    tokens_removed: int

    # Nested selections: element index -> DFSSelection for that element's content
    nested_selections: Dict[int, "DFSSelection"] = field(default_factory=dict)

    # Budget remaining after this level's processing
    remaining_budget: int = 0

    # Whether budget was exhausted at this level or below
    budget_exhausted: bool = False

    @property
    def kept_count(self) -> int:
        return len(self.kept_elements)

    @property
    def removed_count(self) -> int:
        return len(self.removed_elements)

    @property
    def has_removals(self) -> bool:
        return self.removed_count > 0 or any(
            ns.has_removals for ns in self.nested_selections.values()
        )

    @property
    def total_tokens_removed(self) -> int:
        """Total tokens removed including nested levels."""
        total = self.tokens_removed
        for ns in self.nested_selections.values():
            total += ns.total_tokens_removed
        return total


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

    def select_first(
        self,
        elements: List[Element],
        budget: int,
        min_keep: int = 1,
        separator_overhead: int = 0,  # Comma typically doesn't add tokens
    ) -> Selection:
        """
        Select first N elements that fit in budget.

        Args:
            elements: List of elements to select from
            budget: Maximum tokens for content
            min_keep: Minimum elements to keep (even if over budget)
            separator_overhead: Tokens per separator

        Returns:
            Selection with kept and removed elements
        """
        if not elements:
            return Selection(
                kept_elements=[],
                removed_elements=[],
                total_count=0,
                tokens_kept=0,
                tokens_removed=0,
            )

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0

        for i, elem in enumerate(elements):
            elem_tokens = self.tokenizer.count_text(elem.text)
            total_with_sep = elem_tokens + (separator_overhead if kept else 0)

            if tokens_used + total_with_sep <= budget or len(kept) < min_keep:
                kept.append(elem)
                tokens_used += total_with_sep
            else:
                removed.append(elem)

        # Add remaining elements to removed
        removed.extend(elements[len(kept) + len(removed):])

        tokens_removed = sum(
            self.tokenizer.count_text(e.text) for e in removed
        )

        return Selection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=len(elements),
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            placeholder_index=-1,  # Placeholder at end
        )

    def select_first_last(
        self,
        elements: List[Element],
        budget: int,
        separator_overhead: int = 2,
    ) -> Selection:
        """
        Select first and last elements, fitting as many as possible.

        Useful for showing structure while indicating content was trimmed.
        """
        if len(elements) <= 2:
            return self.select_first(elements, budget)

        first_elem = elements[0]
        last_elem = elements[-1]

        first_tokens = self.tokenizer.count_text(first_elem.text)
        last_tokens = self.tokenizer.count_text(last_elem.text)

        # Always try to keep first and last
        if first_tokens + last_tokens + separator_overhead * 2 <= budget:
            kept = [first_elem, last_elem]
            removed = elements[1:-1]
            tokens_kept = first_tokens + last_tokens + separator_overhead * 2
        else:
            # Can only keep first
            kept = [first_elem]
            removed = elements[1:]
            tokens_kept = first_tokens

        tokens_removed = sum(
            self.tokenizer.count_text(e.text) for e in removed
        )

        return Selection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=len(elements),
            tokens_kept=tokens_kept,
            tokens_removed=tokens_removed,
            placeholder_index=1 if len(kept) == 2 else -1,  # Between first and last
        )

    def select_within_budget(
        self,
        elements: List[Element],
        budget: int,
        strategy: str = "first",
        **kwargs
    ) -> Selection:
        """
        Select elements using specified strategy.

        Args:
            elements: Elements to select from
            budget: Token budget for content
            strategy: Selection strategy ("first", "first_last", "distribute")
            **kwargs: Strategy-specific options

        Returns:
            Selection result
        """
        if strategy == "first":
            return self.select_first(elements, budget, **kwargs)
        elif strategy == "first_last":
            return self.select_first_last(elements, budget, **kwargs)
        else:
            # Default to first
            return self.select_first(elements, budget, **kwargs)

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

        return self.tokenizer.count_text(overhead_text)

    def select_dfs(
        self,
        elements: List[Element],
        budget: int,
        parser: ElementParser,
        min_keep: int = 1,
    ) -> DFSSelection:
        """
        Select elements using depth-first strategy for nested structures.

        Greedy DFS with cascading finalization:
        1. Always descend into first element of each structure
        2. Pass remaining budget down to child level
        3. Continue until leaf (atomic value) or budget exhausted
        4. On budget exhaustion, complete first-element chain to deepest level
        5. Unwind recursion, inserting placeholders at each level
        6. Truncate remaining siblings at each level

        Args:
            elements: List of elements at current level
            budget: Token budget for this level and all nested levels
            parser: Parser for recursively parsing nested content
            min_keep: Minimum elements to keep at each level

        Returns:
            DFSSelection with kept/removed elements and nested selections
        """
        if not elements:
            return DFSSelection(
                kept_elements=[],
                removed_elements=[],
                total_count=0,
                tokens_kept=0,
                tokens_removed=0,
                remaining_budget=budget,
                budget_exhausted=False,
            )

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0
        remaining_budget = budget
        budget_exhausted = False
        nested_selections: Dict[int, DFSSelection] = {}

        for i, elem in enumerate(elements):
            # Count tokens for this element
            elem_tokens = self.tokenizer.count_text(elem.text)

            # Check if we can afford this element or must keep it due to min_keep
            can_afford = tokens_used + elem_tokens <= remaining_budget
            must_keep = len(kept) < min_keep

            if can_afford or must_keep:
                # Keep this element
                kept.append(elem)
                tokens_used += elem_tokens
                remaining_budget -= elem_tokens

                # If this element has nested structure, recursively process it
                if elem.has_nested_structure:
                    nested_sel = self.select_dfs(
                        parser.parse(elem.nested_content),
                        remaining_budget,
                        parser,
                        min_keep=min_keep,
                    )
                    nested_selections[i] = nested_sel
                    remaining_budget = nested_sel.remaining_budget
                    budget_exhausted = nested_sel.budget_exhausted

                    # If budget exhausted in nested level, stop processing siblings
                    if budget_exhausted:
                        # Add remaining elements as removed
                        removed.extend(elements[i + 1:])
                        break
            else:
                # Budget exhausted, cannot afford this element
                budget_exhausted = True
                removed.append(elem)

        # Add any remaining elements to removed
        if not budget_exhausted:
            removed.extend(elements[len(kept):])

        # Calculate tokens removed
        tokens_removed = sum(
            self.tokenizer.count_text(e.text) for e in removed
        )

        return DFSSelection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=len(elements),
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            nested_selections=nested_selections,
            remaining_budget=remaining_budget,
            budget_exhausted=budget_exhausted,
        )

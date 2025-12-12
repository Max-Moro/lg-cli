"""
Budget-aware element selection for literal trimming.

Implements algorithms for selecting which elements to keep
within a token budget, including DFS selection for nested structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

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

        For flat Selection: same as tokens_removed.
        For DFSSelection: includes nested removals.

        Returns:
            Total number of tokens removed
        """
        if isinstance(self, DFSSelection):
            return self.total_tokens_removed
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


@dataclass
class DFSSelection(SelectionBase):
    """
    Result of DFS (depth-first) element selection for nested structures.

    Extends SelectionBase with recursive nested selections.
    """
    # Nested selections: element index -> DFSSelection for that element's content
    nested_selections: Dict[int, DFSSelection] = field(default_factory=dict)

    # Budget remaining after this level's processing
    remaining_budget: int = 0

    # Whether budget was exhausted at this level or below
    budget_exhausted: bool = False

    @property
    def has_removals(self) -> bool:
        """Override to check nested selections too."""
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

    def select_dfs(
        self,
        elements: List[Element],
        budget: int,
        parser: ElementParser,
        min_keep: int = 1,
        tuple_size: int = 1,
        preserve_top_level_keys: bool = False,
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
            parser: ElementParser configured for a profile
            min_keep: Minimum elements to keep at each level
            tuple_size: Group elements into tuples (e.g., 2 for k,v pairs, 1 for single elements)
            preserve_top_level_keys: If True, keep all keys at top level (for typed structs)

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

        # Group elements into tuples if needed (tuple_size=1 means single elements)
        if tuple_size > 1:
            groups = [elements[i:i + tuple_size] for i in range(0, len(elements), tuple_size)]
        else:
            groups = [[e] for e in elements]

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0
        remaining_budget = budget
        budget_exhausted = False
        groups_kept = 0
        nested_selections: Dict[int, DFSSelection] = {}

        for group_idx, group in enumerate(groups):
            # Calculate optimized tokens for this group (considering nested optimizations)
            group_optimized_tokens = 0

            # Process each element in group, handling nested structures
            for elem_offset, elem in enumerate(group):
                elem_idx = group_idx * tuple_size + elem_offset
                elem_original_tokens = self.tokenizer.count_text_cached(elem.text)

                # If element has multiline nested structure, recursively process it
                # Single-line nested structures are treated as leaf elements
                if elem.is_multiline_nested:
                    # Recursively optimize nested structure with current remaining budget
                    # Note: preserve_top_level_keys NOT passed to nested calls (only top level preserved)
                    nested_elements = parser.parse(elem.nested_content)
                    nested_sel = self.select_dfs(
                        nested_elements,
                        remaining_budget,
                        parser,
                        min_keep=min_keep,
                        preserve_top_level_keys=False,  # Only preserve at top level
                    )
                    nested_selections[elem_idx] = nested_sel

                    # Calculate optimized size: original tokens minus tokens saved by nested optimization
                    elem_optimized_tokens = elem_original_tokens - nested_sel.total_tokens_removed
                    group_optimized_tokens += elem_optimized_tokens
                else:
                    # Leaf element - use its tokens directly
                    group_optimized_tokens += elem_original_tokens

            # Check if we can afford this group with optimized size
            can_afford = group_optimized_tokens <= remaining_budget

            # Determine if we must keep this group
            must_keep = groups_kept < min_keep
            must_preserve = preserve_top_level_keys  # For typed structs: keep all fields

            if can_afford or must_keep or must_preserve:
                # Keep this group
                kept.extend(group)
                tokens_used += group_optimized_tokens
                remaining_budget -= group_optimized_tokens
                groups_kept += 1

                # Check for budget exhaustion in nested levels
                # For tuple_size=1, check after processing element
                if tuple_size == 1 and len(group) == 1:
                    elem_idx = group_idx
                    if elem_idx in nested_selections:
                        budget_exhausted = nested_selections[elem_idx].budget_exhausted
                        # If budget exhausted in nested level, stop processing siblings
                        # UNLESS preserve_top_level_keys=True (must keep all top-level fields)
                        if budget_exhausted and not preserve_top_level_keys:
                            # Add remaining groups as removed
                            for remaining_group in groups[group_idx + 1:]:
                                removed.extend(remaining_group)
                            break
            else:
                # Budget exhausted, cannot afford this group
                budget_exhausted = True
                # Add this group and all remaining groups to removed
                for remaining_group in groups[group_idx:]:
                    removed.extend(remaining_group)
                # Remove nested selections for removed elements
                for remaining_group_idx in range(group_idx, len(groups)):
                    for elem_offset in range(len(groups[remaining_group_idx])):
                        elem_idx = remaining_group_idx * tuple_size + elem_offset
                        if elem_idx in nested_selections:
                            del nested_selections[elem_idx]
                break

        # Calculate tokens removed
        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed
        )

        # Determine total_count: for tuples it's number of groups, for single elements it's number of elements
        total_count = len(groups) if tuple_size > 1 else len(elements)

        return DFSSelection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=total_count,
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            nested_selections=nested_selections,
            remaining_budget=remaining_budget,
            budget_exhausted=budget_exhausted,
        )

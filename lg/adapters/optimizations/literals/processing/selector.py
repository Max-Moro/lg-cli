"""
Budget-aware element selection for literal trimming.

Implements algorithms for selecting which elements to keep
within a token budget, including DFS selection for nested structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Callable

from lg.stats.tokenizer import TokenService
from ..element_parser import Element, ElementParser
from ..patterns import LiteralProfile, ParsedLiteral, CollectionProfile
from ..components.budgeting import BudgetCalculator


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
        self.budget_calculator = BudgetCalculator(tokenizer)

    def select_first(
        self,
        elements: List[Element],
        budget: int,
        min_keep: int = 1,
        separator_overhead: int = 0,  # Comma typically doesn't add tokens
        tuple_size: int = 1,  # Group elements into tuples (2 for Map.of pairs)
    ) -> Selection:
        """
        Select first N elements that fit in budget.

        Args:
            elements: List of elements to select from
            budget: Maximum tokens for content
            min_keep: Minimum elements to keep (even if over budget)
            separator_overhead: Tokens per separator
            tuple_size: Group elements into tuples (e.g., 2 for k,v pairs)

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

        # Group elements into tuples if tuple_size > 1
        if tuple_size > 1:
            tuples = self._group_into_tuples(elements, tuple_size)
            return self._select_tuples(tuples, budget, min_keep, separator_overhead)

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0

        for i, elem in enumerate(elements):
            elem_tokens = self.tokenizer.count_text_cached(elem.text)
            total_with_sep = elem_tokens + (separator_overhead if kept else 0)

            if tokens_used + total_with_sep <= budget or len(kept) < min_keep:
                kept.append(elem)
                tokens_used += total_with_sep
            else:
                removed.append(elem)

        # Add remaining elements to removed
        removed.extend(elements[len(kept) + len(removed):])

        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed
        )

        return Selection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=len(elements),
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            placeholder_index=-1,  # Placeholder at end
        )

    def _group_into_tuples(
        self,
        elements: List[Element],
        tuple_size: int
    ) -> List[List[Element]]:
        """Group elements into tuples of specified size."""
        tuples = []
        for i in range(0, len(elements), tuple_size):
            tuples.append(elements[i:i + tuple_size])
        return tuples

    def _select_tuples(
        self,
        tuples: List[List[Element]],
        budget: int,
        min_keep: int,
        separator_overhead: int,
    ) -> Selection:
        """Select tuples that fit in budget, treating each tuple as a unit."""
        kept_elements: List[Element] = []
        removed_elements: List[Element] = []
        tokens_used = 0
        tuples_kept = 0

        for tpl in tuples:
            # Calculate tokens for entire tuple
            tuple_text = ", ".join(e.text for e in tpl)
            tuple_tokens = self.tokenizer.count_text_cached(tuple_text)
            total_with_sep = tuple_tokens + (separator_overhead if kept_elements else 0)

            if tokens_used + total_with_sep <= budget or tuples_kept < min_keep:
                kept_elements.extend(tpl)
                tokens_used += total_with_sep
                tuples_kept += 1
            else:
                removed_elements.extend(tpl)

        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed_elements
        )

        # Total count is number of tuples, not individual elements
        total_tuples = len(tuples)

        return Selection(
            kept_elements=kept_elements,
            removed_elements=removed_elements,
            total_count=total_tuples,
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            placeholder_index=-1,
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

        first_tokens = self.tokenizer.count_text_cached(first_elem.text)
        last_tokens = self.tokenizer.count_text_cached(last_elem.text)

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
            self.tokenizer.count_text_cached(e.text) for e in removed
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

    def select_dfs(
        self,
        elements: List[Element],
        budget: int,
        profile: CollectionProfile,
        get_parser_func: Callable[[CollectionProfile], ElementParser],
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
            profile: CollectionProfile for getting parser configuration
            get_parser_func: Function to get parser for a profile
            min_keep: Minimum elements to keep at each level
            tuple_size: Group elements into tuples (e.g., 2 for k,v pairs)
            preserve_top_level_keys: If True, keep all keys at top level (for typed structs)

        Returns:
            DFSSelection with kept/removed elements and nested selections
        """
        # Get parser through callback function
        parser = get_parser_func(profile)

        # Handle tuple grouping for Map.of style patterns
        if tuple_size > 1:
            return self._select_dfs_tuples(
                elements, budget, profile, get_parser_func, min_keep, tuple_size, preserve_top_level_keys
            )

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
            # Count original tokens for this element
            elem_original_tokens = self.tokenizer.count_text_cached(elem.text)

            # Check if we can afford this element or must keep it due to min_keep
            can_afford = elem_original_tokens <= remaining_budget
            must_keep = len(kept) < min_keep
            must_preserve = preserve_top_level_keys  # For typed structs: keep all fields

            if can_afford or must_keep or must_preserve:
                # Keep this element
                kept.append(elem)

                # If this element has multiline nested structure, recursively process it
                # Single-line nested structures are treated as leaf elements
                if elem.is_multiline_nested:
                    # Recursively optimize nested structure with current remaining budget
                    # Note: preserve_top_level_keys NOT passed to nested calls (only top level preserved)
                    nested_elements = parser.parse(elem.nested_content)
                    nested_sel = self.select_dfs(
                        nested_elements,
                        remaining_budget,
                        profile,
                        get_parser_func,
                        min_keep=min_keep,
                        preserve_top_level_keys=False,  # Only preserve at top level
                    )
                    nested_selections[i] = nested_sel

                    # Calculate optimized size of this element
                    # (original tokens minus tokens saved by nested optimization)
                    elem_optimized_tokens = elem_original_tokens - nested_sel.total_tokens_removed

                    # Subtract optimized size from budget
                    tokens_used += elem_optimized_tokens
                    remaining_budget -= elem_optimized_tokens
                    budget_exhausted = nested_sel.budget_exhausted

                    # If budget exhausted in nested level, stop processing siblings
                    # UNLESS preserve_top_level_keys=True (must keep all top-level fields)
                    if budget_exhausted and not preserve_top_level_keys:
                        # Add remaining elements as removed
                        removed.extend(elements[i + 1:])
                        break
                else:
                    # Leaf element - subtract its tokens directly
                    tokens_used += elem_original_tokens
                    remaining_budget -= elem_original_tokens
            else:
                # Budget exhausted, cannot afford this element
                budget_exhausted = True
                # Add this element and all remaining to removed
                removed.extend(elements[i:])
                break

        # Calculate tokens removed
        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed
        )

        # Calculate total tokens removed including nested
        total_tokens_removed_including_nested = tokens_removed
        for nested_sel in nested_selections.values():
            total_tokens_removed_including_nested += nested_sel.total_tokens_removed

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

    def _select_dfs_tuples(
        self,
        elements: List[Element],
        budget: int,
        profile: CollectionProfile,
        get_parser_func: Callable[[CollectionProfile], ElementParser],
        min_keep: int,
        tuple_size: int,
        preserve_top_level_keys: bool = False,
    ) -> DFSSelection:
        """
        DFS selection with tuple grouping (for Map.of style patterns).

        Groups elements into tuples and applies DFS recursively to nested structures
        within tuple elements.
        """
        # Get parser through callback function
        parser = get_parser_func(profile)

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

        # Group elements into tuples
        tuples = self._group_into_tuples(elements, tuple_size)

        kept: List[Element] = []
        removed: List[Element] = []
        tokens_used = 0
        remaining_budget = budget
        budget_exhausted = False
        tuples_kept = 0
        nested_selections: Dict[int, DFSSelection] = {}

        for tuple_idx, tpl in enumerate(tuples):
            # Process each element in tuple with DFS if nested
            tuple_optimized_tokens = 0

            # First pass: calculate original size and process nested structures
            for elem_offset, elem in enumerate(tpl):
                elem_idx = tuple_idx * tuple_size + elem_offset
                elem_original_tokens = self.tokenizer.count_text_cached(elem.text)

                # If element has multiline nested structure, recursively process it
                if elem.is_multiline_nested:
                    # Pass full remaining budget to recursion (not reduced by previous tuple elements)
                    # Note: preserve_top_level_keys NOT passed to nested calls
                    nested_sel = self.select_dfs(
                        parser.parse(elem.nested_content),
                        remaining_budget,
                        profile,
                        get_parser_func,
                        min_keep=min_keep,
                        preserve_top_level_keys=False,  # Only preserve at top level
                    )
                    nested_selections[elem_idx] = nested_sel

                    # Calculate element tokens after nested optimization
                    # Original size minus tokens saved by nested optimization
                    elem_optimized_tokens = elem_original_tokens - nested_sel.total_tokens_removed
                    tuple_optimized_tokens += elem_optimized_tokens
                else:
                    # Leaf element - use its tokens directly
                    tuple_optimized_tokens += elem_original_tokens

            # Check if we can afford this tuple with optimized size
            can_afford = tokens_used + tuple_optimized_tokens <= remaining_budget

            # Apply must_keep at all levels to preserve recursion chain
            must_keep = tuples_kept < min_keep
            must_preserve = preserve_top_level_keys  # For typed structs: keep all fields

            if can_afford or must_keep or must_preserve:
                kept.extend(tpl)
                tokens_used += tuple_optimized_tokens
                remaining_budget -= tuple_optimized_tokens
                tuples_kept += 1
            else:
                budget_exhausted = True
                removed.extend(tpl)
                # Remove nested selections for removed tuples
                for elem_offset in range(len(tpl)):
                    elem_idx = tuple_idx * tuple_size + elem_offset
                    if elem_idx in nested_selections:
                        del nested_selections[elem_idx]

        # Calculate tokens removed
        tokens_removed = sum(
            self.tokenizer.count_text_cached(e.text) for e in removed
        )

        return DFSSelection(
            kept_elements=kept,
            removed_elements=removed,
            total_count=len(tuples),
            tokens_kept=tokens_used,
            tokens_removed=tokens_removed,
            nested_selections=nested_selections,
            remaining_budget=remaining_budget,
            budget_exhausted=budget_exhausted,
        )

"""
Public API optimization.
Filters code to show only public/exported elements.
"""

from __future__ import annotations

from typing import cast

from ...context import ProcessingContext


class PublicApiOptimizer:
    """Handles filtering code for public API only."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        """
        from ...code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply public API filtering.
        Removes private/protected elements, keeping only public/exported ones.

        Args:
            context: Processing context with document and editor
        """
        # Collect all private elements using analyzer
        private_elements = context.code_analyzer.collect_private_elements_for_public_api()

        # First compute ranges with decorators for all elements
        element_ranges = [
            (context.code_analyzer.get_element_range_with_decorators(elem), elem)
            for elem in private_elements
        ]

        # Sort by position (in reverse order for safe removal)
        element_ranges.sort(key=lambda x: x[0][0], reverse=True)

        # Remove private elements with appropriate placeholders
        for (start_char, end_char), private_element in element_ranges:
            context.add_placeholder(private_element.element_type, start_char, end_char)

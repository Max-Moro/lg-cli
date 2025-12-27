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
        # Get collector (cached in context, uses pre-loaded descriptor)
        collector = context.get_collector()

        # Get comment analyzer for extending ranges
        comment_analyzer = context.get_comment_analyzer()

        # Get private elements (cached, already filtered for nesting)
        private_elements = collector.get_private()

        # Sort by position in reverse order for safe removal
        private_elements.sort(key=lambda e: e.start_byte, reverse=True)

        # Remove private elements with appropriate placeholders
        for element in private_elements:
            # Get extended range including associated comments
            start_byte, end_byte = comment_analyzer.get_associated_comments_range(element.node)

            # Use element's own boundaries if they extend beyond node
            # (e.g., decorators before the element)
            if element.start_byte < start_byte:
                start_byte = element.start_byte
            if element.end_byte > end_byte:
                end_byte = element.end_byte

            start_char = context.doc.byte_to_char_position(start_byte)
            end_char = context.doc.byte_to_char_position(end_byte)
            context.add_placeholder(element.profile.name, start_char, end_char)

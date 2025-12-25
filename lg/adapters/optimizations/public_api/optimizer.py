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

        # Get private elements (cached, already filtered for nesting)
        private_elements = collector.get_private()

        # Sort by position in reverse order for safe removal
        private_elements.sort(key=lambda e: e.start_byte, reverse=True)

        # Remove private elements with appropriate placeholders
        for element in private_elements:
            start_char = context.doc.byte_to_char_position(element.start_byte)
            end_char = context.doc.byte_to_char_position(element.end_byte)
            context.add_placeholder(element.profile.name, start_char, end_char)

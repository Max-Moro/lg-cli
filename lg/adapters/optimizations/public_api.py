"""
Public API optimization.
Filters code to show only public/exported elements.
"""

from __future__ import annotations

from typing import cast

from ..context import ProcessingContext


class PublicApiOptimizer:
    """Handles filtering code for public API only."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply public API filtering.
        Removes private/protected elements, keeping only public/exported ones.
        
        Args:
            context: Processing context with document and editor
        """
        # Get language-specific visibility analyzer
        visibility_analyzer = self.adapter.create_visibility_analyzer(context.doc)
        
        # Collect all private elements using the new analyzer
        private_elements = visibility_analyzer.collect_all_private_elements(context)
        
        # Get structure analyzer for handling decorators
        structure_analyzer = self.adapter.create_structure_analyzer(context.doc)
        
        # Sort by position (reverse order for safe removal) 
        # Using structure analyzer for getting ranges with decorators
        private_elements.sort(key=lambda x: structure_analyzer.get_element_range_with_decorators(x.node)[0], reverse=True)
        
        # Remove private elements with appropriate placeholders
        for private_element in private_elements:
            # Get extended range including decorators using language-specific logic
            start_byte, end_byte = structure_analyzer.get_element_range_with_decorators(private_element.node)
            start_line = context.doc.get_line_number_for_byte(start_byte)
            end_line = context.doc.get_line_number_for_byte(end_byte)

            # Add appropriate placeholder using custom range
            context.add_placeholder(private_element.element_type, start_byte, end_byte, start_line, end_line)

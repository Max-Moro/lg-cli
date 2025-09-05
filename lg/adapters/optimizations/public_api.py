"""
Public API optimization.
Filters code to show only public/exported elements.
"""

from __future__ import annotations

from ..context import ProcessingContext


class PublicApiOptimizer:
    """Handles filtering code for public API only."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        self.adapter = adapter
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply public API filtering.
        Removes private/protected elements, keeping only public/exported ones.
        
        Args:
            context: Processing context with document and editor
        """
        # Find all functions and methods
        functions = context.query("functions")
        private_ranges = []
        
        for node, capture_name in functions:
            if capture_name in ("function_name", "method_name"):
                function_def = node.parent
                # Check element visibility using adapter's language-specific logic
                is_public = self.adapter.is_public_element(function_def, context)
                is_exported = self.adapter.is_exported_element(function_def, context)
                
                # For methods - consider access modifiers
                # For top-level functions - check export status  
                if capture_name == "method_name":
                    # Method removed if private/protected
                    if not is_public:
                        start_byte, end_byte = context.get_node_range(function_def)
                        private_ranges.append((start_byte, end_byte, function_def))
                else:  # function_name
                    # Top-level function removed if not exported
                    if not is_exported:
                        start_byte, end_byte = context.get_node_range(function_def)
                        private_ranges.append((start_byte, end_byte, function_def))
        
        # Also check classes
        classes = context.query("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                # Check class export status
                is_exported = self.adapter.is_exported_element(class_def, context)
                
                # For top-level classes, export is primary consideration
                if not is_exported:
                    start_byte, end_byte = context.get_node_range(class_def)
                    private_ranges.append((start_byte, end_byte, class_def))
        
        # Sort by position (reverse order for safe removal)
        private_ranges.sort(key=lambda x: x[0], reverse=True)
        
        # Remove private elements with placeholders
        for start_byte, end_byte, element in private_ranges:
            start_line, end_line = context.get_line_range(element)
            lines_count = end_line - start_line + 1
            
            placeholder = context.placeholder_gen.create_custom_placeholder(
                "… private element omitted (−{lines})",
                {"lines": lines_count},
                style=self.adapter.cfg.placeholders.style
            )
            
            context.editor.add_replacement(
                start_byte, end_byte, placeholder,
                type="private_element_removal",
                is_placeholder=True,
                lines_removed=lines_count
            )
            
            context.metrics.increment("code.removed.private_elements")
            context.metrics.add_lines_saved(lines_count)
            context.metrics.mark_placeholder_inserted()

"""
Public API optimization.
Filters code to show only public/exported elements.
"""

from __future__ import annotations

from typing import cast

from ..code_structure_utils import collect_function_like_nodes, get_element_range_with_decorators
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
        # Find all functions and methods using universal structure analysis
        functions = context.doc.query("functions")
        private_elements = []  # List of (element_node, element_type)
        
        # Group function-like captures using universal utilities
        function_groups = collect_function_like_nodes(functions)
        
        for func_def, func_data in function_groups.items():
            element_type = func_data["type"]
            
            # Check element visibility using adapter's language-specific logic
            is_public = self.adapter.is_public_element(func_def, context.doc)
            is_exported = self.adapter.is_exported_element(func_def, context.doc)
            
            # Universal logic based on element type
            should_remove = False
            
            if element_type == "method":
                # Method removed if private/protected
                should_remove = not is_public
            else:  # function, arrow_function, etc.
                # Top-level function removed if not exported
                should_remove = not is_exported
            
            if should_remove:
                private_elements.append((func_def, element_type))
        
        # Also check classes
        classes = context.doc.query("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                # Check class export status
                is_exported = self.adapter.is_exported_element(class_def, context.doc)
                
                # For top-level classes, export is primary consideration
                if not is_exported:
                    private_elements.append((class_def, "class"))
        
        # Check interfaces (TypeScript/similar languages)
        interfaces = context.doc.query_opt("interfaces")
        for node, capture_name in interfaces:
            if capture_name == "interface_name":
                interface_def = node.parent
                is_exported = self.adapter.is_exported_element(interface_def, context.doc)

                if not is_exported:
                    private_elements.append((interface_def, "interface"))
        
        # Check type aliases (TypeScript/similar languages)
        types = context.doc.query_opt("types")
        for node, capture_name in types:
            if capture_name == "type_name":
                type_def = node.parent
                is_exported = self.adapter.is_exported_element(type_def, context.doc)

                if not is_exported:
                    private_elements.append((type_def, "type"))
        
        # Sort by position (reverse order for safe removal)
        private_elements.sort(key=lambda x: get_element_range_with_decorators(x[0], context.doc)[0], reverse=True)
        
        # Remove private elements with appropriate placeholders
        for element, element_type in private_elements:
            self._remove_element_with_decorators(context, element, element_type)

    def _remove_element_with_decorators(self, context: ProcessingContext, element, element_type: str) -> None:
        """
        Remove element including its decorators/annotations.
        
        Args:
            context: Processing context
            element: Element node to remove
            element_type: Type of element for appropriate placeholder
        """
        # Get extended range including decorators
        start_byte, end_byte = get_element_range_with_decorators(element, context.doc)
        start_line = context.doc.get_line_number_for_byte(start_byte)
        end_line = context.doc.get_line_number_for_byte(end_byte)
        
        # Add appropriate placeholder using custom range
        context.add_placeholder(element_type, start_byte, end_byte, start_line, end_line)

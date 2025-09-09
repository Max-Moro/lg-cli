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
        # Find all functions and methods
        functions = context.doc.query("functions")
        private_elements = []  # List of (element_node, element_type)
        
        for node, capture_name in functions:
            if capture_name in ("function_name", "method_name"):
                function_def = node.parent
                # Check element visibility using adapter's language-specific logic
                is_public = self.adapter.is_public_element(function_def, context.doc)
                is_exported = self.adapter.is_exported_element(function_def, context.doc)
                
                # For methods - consider access modifiers
                # For top-level functions - check export status  
                if capture_name == "method_name":
                    # Method removed if private/protected
                    if not is_public:
                        private_elements.append((function_def, "method"))
                else:  # function_name
                    # Top-level function removed if not exported
                    if not is_exported:
                        private_elements.append((function_def, "function"))
        
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
        private_elements.sort(key=lambda x: context.doc.get_node_range(x[0])[0], reverse=True)
        
        # Remove private elements with appropriate placeholders
        for element, element_type in private_elements:
            if element_type == "function":
                context.add_function_placeholder(element)
            elif element_type == "method":
                context.add_method_placeholder(element)
            elif element_type == "class":
                context.add_class_placeholder(element)
            elif element_type == "interface":
                context.add_interface_placeholder(element)
            elif element_type == "type":
                context.add_type_placeholder(element)

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
        # Get language-specific structure analyzer
        analyzer = self.adapter.create_structure_analyzer(context.doc)
        
        # Find all functions and methods using language-specific structure analysis
        functions = context.doc.query("functions")
        private_elements = []  # List of (element_node, element_type)
        
        # Group function-like captures using language-specific utilities
        function_groups = analyzer.collect_function_like_elements(functions)
        
        for func_def, func_group in function_groups.items():
            element_type = func_group.element_type
            
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
        
        # Check variable assignments
        assignments = context.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                # Get the assignment statement node
                assignment_def = node.parent
                if assignment_def:
                    # Check if variable is public using name-based rules
                    is_public = self.adapter.is_public_element(assignment_def, context.doc)
                    is_exported = self.adapter.is_exported_element(assignment_def, context.doc)
                    
                    # For top-level variables, check public/exported status
                    should_remove = not (is_public and is_exported)
                    
                    if should_remove:
                        private_elements.append((assignment_def, "variable"))
        
        # Sort by position (reverse order for safe removal) 
        # Using analyzer for getting ranges with decorators
        private_elements.sort(key=lambda x: analyzer.get_element_range_with_decorators(x[0])[0], reverse=True)
        
        # Remove private elements with appropriate placeholders
        for element, element_type in private_elements:
            # Get extended range including decorators using language-specific logic
            start_byte, end_byte = analyzer.get_element_range_with_decorators(element)
            start_line = context.doc.get_line_number_for_byte(start_byte)
            end_line = context.doc.get_line_number_for_byte(end_byte)

            # Add appropriate placeholder using custom range
            context.add_placeholder(element_type, start_byte, end_byte, start_line, end_line)

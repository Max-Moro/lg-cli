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
        
        # Check namespaces (TypeScript)
        namespaces = context.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                is_exported = self.adapter.is_exported_element(namespace_def, context.doc)

                if not is_exported:
                    private_elements.append((namespace_def, "namespace"))
        
        # Check enums (TypeScript)
        enums = context.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                is_exported = self.adapter.is_exported_element(enum_def, context.doc)

                if not is_exported:
                    private_elements.append((enum_def, "enum"))

        # Check class fields and methods (TypeScript)
        class_fields = context.doc.query_opt("class_fields")
        for node, capture_name in class_fields:
            if capture_name in ("field_name", "method_name"):
                # Get the parent definition node
                field_def = node.parent
                if field_def:
                    # Check if field/method is public
                    is_public = self.adapter.is_public_element(field_def, context.doc)
                    
                    # Remove private/protected class members
                    if not is_public:
                        element_type = "field" if capture_name == "field_name" else "method"
                        # For fields, extend range to include semicolon if present
                        element_with_punctuation = self._extend_range_for_semicolon(field_def, context.doc) if element_type == "field" else field_def
                        private_elements.append((element_with_punctuation, element_type))

        # Check imports (remove non-re-exported imports)
        imports = context.doc.query_opt("imports")
        for node, capture_name in imports:
            if capture_name == "import":
                # For public API mode, only keep imports that are re-exported
                # For simplicity, remove all imports that are not explicitly re-exported
                # This is a conservative approach - could be refined to check for re-exports
                import_text = context.doc.get_node_text(node)

                # Keep only side-effect imports (no named imports)
                if not any(keyword in import_text for keyword in ["{", "import ", "* as", "from"]):
                    continue  # Keep side-effect imports

                # Check if this import is re-exported elsewhere
                # For now, remove all regular imports in public API mode
                private_elements.append((node, "import"))

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
    
    def _extend_range_for_semicolon(self, node, doc):
        """
        Extends node range to include trailing semicolon if present.
        
        This is needed for TypeScript fields where the semicolon is a separate sibling node.
        Without including it, adjacent field placeholders cannot be collapsed properly.
        
        Args:
            node: Tree-sitter node (typically a field definition)
            doc: TreeSitterDocument instance
            
        Returns:
            Node with potentially extended range, or original node if no semicolon found
        """
        # Check if there's a semicolon immediately after this node
        parent = node.parent
        if not parent:
            return node
        
        # Find this node's position among siblings
        siblings = parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling == node:
                node_index = i
                break
        
        if node_index is None:
            return node
        
        # Check if the next sibling is a semicolon
        if node_index + 1 < len(siblings):
            next_sibling = siblings[node_index + 1]
            if (next_sibling.type == ";" or 
                doc.get_node_text(next_sibling).strip() == ";"):
                # Create a synthetic range that includes the semicolon
                return self._create_extended_range_node(node, next_sibling)
        
        return node
    
    def _create_extended_range_node(self, original_node, semicolon_node):
        """
        Creates a synthetic node-like object with extended range.
        
        This is a workaround since Tree-sitter nodes are immutable.
        We create a simple object that has the same interface for range operations.
        """
        class ExtendedRangeNode:
            def __init__(self, start_node, end_node):
                self.start_byte = start_node.start_byte
                self.end_byte = end_node.end_byte
                self.start_point = start_node.start_point
                self.end_point = end_node.end_point
                self.type = start_node.type
                self.parent = start_node.parent
                # Copy other commonly used attributes
                for attr in ['children', 'text']:
                    if hasattr(start_node, attr):
                        setattr(self, attr, getattr(start_node, attr))
        
        return ExtendedRangeNode(original_node, semicolon_node)

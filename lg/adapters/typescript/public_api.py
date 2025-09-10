"""
TypeScript-specific public API optimization logic.
"""

from __future__ import annotations

from typing import List, Tuple

from ..context import ProcessingContext
from ..tree_sitter_support import Node


class TypeScriptPublicApiCollector:
    """TypeScript-specific logic for collecting private elements in public API mode."""
    
    def __init__(self, adapter):
        self.adapter = adapter
    
    def collect_private_elements(self, context: ProcessingContext) -> List[Tuple[Node, str]]:
        """Collect TypeScript-specific private elements for removal."""
        private_elements = []
        
        # TypeScript-specific elements
        self._collect_interfaces(context, private_elements)
        self._collect_types(context, private_elements)
        self._collect_namespaces(context, private_elements)
        self._collect_enums(context, private_elements)
        self._collect_class_members(context, private_elements)
        self._collect_imports(context, private_elements)
        self._collect_variables(context, private_elements)
        
        return private_elements
    
    def _collect_interfaces(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-exported interfaces."""
        interfaces = context.doc.query_opt("interfaces")
        for node, capture_name in interfaces:
            if capture_name == "interface_name":
                interface_def = node.parent
                is_exported = self.adapter.is_exported_element(interface_def, context.doc)
                if not is_exported:
                    private_elements.append((interface_def, "interface"))
    
    def _collect_types(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-exported type aliases."""
        types = context.doc.query_opt("types")
        for node, capture_name in types:
            if capture_name == "type_name":
                type_def = node.parent
                is_exported = self.adapter.is_exported_element(type_def, context.doc)
                if not is_exported:
                    private_elements.append((type_def, "type"))
    
    def _collect_namespaces(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-exported namespaces."""
        namespaces = context.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                is_exported = self.adapter.is_exported_element(namespace_def, context.doc)
                if not is_exported:
                    private_elements.append((namespace_def, "namespace"))
    
    def _collect_enums(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-exported enums."""
        enums = context.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                is_exported = self.adapter.is_exported_element(enum_def, context.doc)
                if not is_exported:
                    private_elements.append((enum_def, "enum"))
    
    def _collect_class_members(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect private/protected class members."""
        class_fields = context.doc.query_opt("class_fields")
        for node, capture_name in class_fields:
            if capture_name in ("field_name", "method_name"):
                field_def = node.parent
                if field_def:
                    is_public = self.adapter.is_public_element(field_def, context.doc)
                    if not is_public:
                        element_type = "field" if capture_name == "field_name" else "method"
                        # For fields, extend range to include semicolon if present
                        element_with_punctuation = self._extend_range_for_semicolon(field_def, context.doc) if element_type == "field" else field_def
                        private_elements.append((element_with_punctuation, element_type))
    
    def _collect_imports(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-re-exported imports."""
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
    
    def _collect_variables(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]) -> None:
        """Collect non-exported variables."""
        assignments = context.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                assignment_def = node.parent
                if assignment_def:
                    is_public = self.adapter.is_public_element(assignment_def, context.doc)
                    is_exported = self.adapter.is_exported_element(assignment_def, context.doc)
                    
                    # For top-level variables, check public/exported status
                    should_remove = not (is_public and is_exported)
                    
                    if should_remove:
                        private_elements.append((assignment_def, "variable"))
    
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

"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import Optional

from ..context import ProcessingContext
from ..tree_sitter_support import Node


class FunctionBodyOptimizer:
    """Handles function body stripping optimization."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        self.adapter = adapter
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply function body stripping based on configuration.
        
        Args:
            context: Processing context with document and editor
        """
        cfg = self.adapter.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Find all function bodies and strip them
        functions = context.query("functions")
        
        for node, capture_name in functions:
            # Support both function_body and method_body
            if capture_name in ("function_body", "method_body"):
                start_line, end_line = context.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Check if this body should be stripped
                should_strip = self.should_strip_function_body(node, lines_count, cfg, context)
                
                if should_strip:
                    # Determine type (method vs function)
                    func_type = "method" if capture_name == "method_body" or context.is_method(node) else "function"
                    
                    context.remove_function_body(
                        node, 
                        func_type=func_type,
                        placeholder_style=self.adapter.cfg.placeholders.style
                    )
        
        # Give adapter a chance to handle language-specific cases (e.g., arrow functions)
        self.adapter.hook__strip_function_bodies(context)
    
    def should_strip_function_body(
        self, 
        body_node: Node, 
        lines_count: int,
        cfg, 
        context: ProcessingContext
    ) -> bool:
        """
        Determine if a function body should be stripped based on configuration.
        
        Args:
            body_node: Tree-sitter node representing function body
            lines_count: Number of lines in the function body
            cfg: Function body stripping configuration
            context: Processing context
            
        Returns:
            True if body should be stripped, False otherwise
        """
        if isinstance(cfg, bool):
            # For boolean True, apply smart logic:
            # don't strip single-line bodies (important for arrow functions)
            if cfg and lines_count <= 1:
                return False
            return cfg
        
        # If config is an object, apply complex logic
        if hasattr(cfg, 'mode'):
            if cfg.mode == "none":
                return False
            elif cfg.mode == "all":
                return True
            elif cfg.mode == "large_only":
                return lines_count >= getattr(cfg, 'min_lines', 5)
            elif cfg.mode == "public_only":
                # Strip bodies only for public functions
                parent_function = self._find_function_definition(body_node)
                if parent_function:
                    is_public = self.adapter.is_public_element(parent_function, context)
                    is_exported = self.adapter.is_exported_element(parent_function, context)
                    return is_public or is_exported
                return False
            elif cfg.mode == "non_public":
                # Strip bodies only for private functions
                parent_function = self._find_function_definition(body_node)
                if parent_function:
                    is_public = self.adapter.is_public_element(parent_function, context)
                    is_exported = self.adapter.is_exported_element(parent_function, context)
                    return not (is_public or is_exported)
                return False
        
        return False
    
    def _find_function_definition(self, body_node: Node) -> Optional[Node]:
        """
        Find the function definition node for a given function body.
        
        Args:
            body_node: Function body node to find parent for
            
        Returns:
            Function definition node or None if not found
        """
        current = body_node.parent
        while current:
            if current.type in ("function_definition", "method_definition", "arrow_function"):
                return current
            current = current.parent
        return None

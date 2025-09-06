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
        functions = context.doc.query("functions")
        
        for node, capture_name in functions:
            # Support both function_body and method_body
            if capture_name in ("function_body", "method_body"):
                start_line, end_line = context.doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Check if this body should be stripped
                should_strip = self.should_strip_function_body(node, lines_count, cfg, context)
                
                if should_strip:
                    # Determine type (method vs function)
                    func_type = "method" if capture_name == "method_body" or self.is_method(node) else "function"
                    
                    # For Python adapter, preserve docstrings when stripping function bodies
                    if self.adapter.name == "python":
                        self.adapter.remove_function_body_preserve_docstring(
                            node, 
                            func_type=func_type,
                            placeholder_style=self.adapter.cfg.placeholders.style
                        )
                    else:
                        self.remove_function_body(
                            context,
                            node, 
                            func_type=func_type,
                            placeholder_style=self.adapter.cfg.placeholders.style
                        )

    @staticmethod
    def remove_function_body(
            context: ProcessingContext,
            body_node: Node,
            func_type: str = "function",
            placeholder_style: str = "inline"
    ) -> None:
        """
        Удаляет тело функции/метода с автоматическим учетом метрик.
        """
        start_byte, end_byte = context.doc.get_node_range(body_node)
        start_line, end_line = context.doc.get_line_range(body_node)
        lines_count = end_line - start_line + 1

        # Создаем плейсхолдер в зависимости от типа
        if func_type == "method":
            placeholder = context.placeholder_gen.create_method_placeholder(
                lines_removed=lines_count,
                bytes_removed=end_byte - start_byte,
                style=placeholder_style
            )
            context.metrics.mark_method_removed()
        else:
            placeholder = context.placeholder_gen.create_function_placeholder(
                lines_removed=lines_count,
                bytes_removed=end_byte - start_byte,
                style=placeholder_style
            )
            context.metrics.mark_function_removed()

        # Добавляем правку
        context.editor.add_replacement(
            start_byte, end_byte, placeholder,
            type=f"{func_type}_body_removal",
            is_placeholder=True,
            lines_removed=lines_count
        )

        context.metrics.add_lines_saved(lines_count)
        context.metrics.add_bytes_saved(end_byte - start_byte - len(placeholder.encode('utf-8')))
        context.metrics.mark_placeholder_inserted()

    @staticmethod
    def is_method(function_body_node: Node) -> bool:
        """
        Определяет, является ли узел function_body методом класса.
        Проходит вверх по дереву в поисках class_definition или class_declaration.
        """
        current = function_body_node.parent
        while current:
            if current.type in ("class_definition", "class_declaration"):
                return True
            current = current.parent
        return False

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
            # But allow override for complex config modes
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
    
    @staticmethod
    def _find_function_definition(body_node: Node) -> Optional[Node]:
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

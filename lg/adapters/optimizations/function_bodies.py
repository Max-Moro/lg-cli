"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import Optional, cast

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
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
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
        
        # Group captures by function_definition
        function_groups = {}
        for node, capture_name in functions:
            if capture_name == "function_definition":
                function_groups[node] = {"definition": node}
            elif capture_name in ("function_body", "method_body"):
                # Find corresponding function_definition
                func_def = self._find_function_definition_for_body(node, [n for n, c in functions if c == "function_definition"])
                if func_def:
                    if func_def not in function_groups:
                        function_groups[func_def] = {"definition": func_def}
                    function_groups[func_def]["body"] = node
                    function_groups[func_def]["body_type"] = capture_name
                else:
                    # Fallback for standalone body
                    function_groups[node] = {"body": node, "body_type": capture_name}

        # Process each function group
        for func_data in function_groups.values():
            if "body" not in func_data:
                continue  # Skip if no body found
                
            body_node = func_data["body"]
            body_type = func_data.get("body_type", "function_body")
            func_def = func_data.get("definition")
            
            start_line, end_line = context.doc.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Check if this body should be stripped
            should_strip = self.should_strip_function_body(body_node, lines_count, cfg, context)
            
            if should_strip:
                # Determine type (method vs function)
                func_type = "method" if body_type == "method_body" or self.is_method(body_node) else "function"
                
                self.adapter.hook__remove_function_body(
                    root_optimizer=self,
                    context=context,
                    func_def=func_def, # Use adapter-specific logic with function_definition
                    body_node=body_node,
                    func_type=func_type
                )

    @staticmethod
    def remove_function_body(
            context: ProcessingContext,
            body_node: Node,
            func_type: str
    ) -> None:
        """
        Удаляет тело функции/метода с автоматическим учетом метрик.
        """
        start_byte, end_byte = context.doc.get_node_range(body_node)

        FunctionBodyOptimizer.apply_function_body_removal(
            context=context,
            start_byte=start_byte,
            end_byte=end_byte,
            func_type=func_type,
        )

    @staticmethod
    def apply_function_body_removal(
            context: ProcessingContext,
            start_byte: int,
            end_byte: int,
            func_type: str,
            placeholder_prefix: str = ""
    ) -> None:
        """
        Общий helper для применения удаления тела функции с placeholder'ами и метриками.
        
        Args:
            context: Контекст обработки
            start_byte: Начальная позиция для удаления
            end_byte: Конечная позиция для удаления
            func_type: Тип функции ("function" или "method")
            placeholder_prefix: Префикс для placeholder'а (например "\n    ")
        """

        """
        Удаляет тело функции/метода с автоматическим учетом метрик.
        """
        start_line = context.doc.get_line_number_for_byte(start_byte)
        end_line = context.doc.get_line_number_for_byte(end_byte)

        context.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line,
            placeholder_type=func_type,
            placeholder_prefix=placeholder_prefix
        )
        if func_type == "method":
            context.metrics.mark_method_removed()
        else:
            context.metrics.mark_function_removed()

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
    def _find_function_definition_for_body(body_node: Node, function_definitions: list) -> Optional[Node]:
        """
        Find the function_definition that contains the given body_node.
        
        Args:
            body_node: The body node to find parent for
            function_definitions: List of function_definition nodes
            
        Returns:
            Function definition that contains the body, or None
        """
        for func_def in function_definitions:
            # Check if body_node is within func_def range
            if (func_def.start_byte <= body_node.start_byte and 
                body_node.end_byte <= func_def.end_byte):
                return func_def
        return None


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

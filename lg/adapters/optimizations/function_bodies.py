"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import cast

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
        
        # Get language-specific unified code analyzer
        analyzer = self.adapter.create_code_analyzer(context.doc)
        
        # Find all function bodies and strip them using language-specific analysis
        functions = context.doc.query("functions")
        
        # Group function-like captures using language-specific utilities
        function_groups = analyzer.collect_function_like_elements(functions)

        # Process each function group
        for func_def, func_group in function_groups.items():
            if func_group.body_node is None:
                continue  # Skip if no body found
                
            body_node = func_group.body_node
            element_type = func_group.element_info.element_type
            
            start_line, end_line = context.doc.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Check if this body should be stripped
            should_strip = self.should_strip_function_body(func_group.element_info.in_public_api, lines_count, cfg)
            
            if should_strip:
                self.adapter.hook__remove_function_body(
                    root_optimizer=self,
                    context=context,
                    func_def=func_def,
                    body_node=body_node,
                    func_type=element_type
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

        context.add_placeholder(func_type + "_body", start_byte, end_byte, start_line, end_line,
            placeholder_prefix=placeholder_prefix
        )

    def should_strip_function_body(
        self, 
        in_public_api: True,
        lines_count: int,
        cfg
    ) -> bool:
        """
        Determine if a function body should be stripped based on configuration.
        
        Args:
            in_public_api: A function or method is part of a public API
            lines_count: Number of lines in the function body
            cfg: Function body stripping configuration
            
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
                return lines_count >= cfg.min_lines
            elif cfg.mode == "public_only":
                # Strip bodies only for public functions
                return in_public_api
            elif cfg.mode == "non_public":
                # Strip bodies only for private functions
                return not in_public_api
        
        return False

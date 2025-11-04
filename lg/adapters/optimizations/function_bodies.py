"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import cast, Union

from ..code_model import FunctionBodyConfig
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class FunctionBodyOptimizer:
    """Handles function body stripping optimization."""
    
    def __init__(self, cfg: Union[bool, FunctionBodyConfig], adapter):
        """
        Initialize with parent adapter for language-specific checks.
        """
        self.cfg = cfg
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply function body stripping based on configuration.
        
        Args:
            context: Processing context with document and editor
        """
        if not self.cfg:
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
            should_strip = self.should_strip_function_body(func_group.element_info.in_public_api, lines_count)
            
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
        start_char, end_char = context.doc.get_node_range(body_node)

        FunctionBodyOptimizer.apply_function_body_removal(
            context=context,
            start_char=start_char,
            end_char=end_char,
            func_type=func_type,
        )

    @staticmethod
    def apply_function_body_removal(
            context: ProcessingContext,
            start_char: int,
            end_char: int,
            func_type: str,
            placeholder_prefix: str = ""
    ) -> None:
        """
        Общий helper для применения удаления тела функции с placeholder'ами и метриками.
        
        Args:
            context: Контекст обработки
            start_char: Начальная позиция для удаления
            end_char: Конечная позиция для удаления
            func_type: Тип функции ("function" или "method")
            placeholder_prefix: Префикс для placeholder'а (например "\n    ")
        """

        """
        Удаляет тело функции/метода с автоматическим учетом метрик.
        """
        start_line = context.doc.get_line_number(start_char)
        end_line = context.doc.get_line_number(end_char)

        context.add_placeholder(func_type + "_body", start_char, end_char, start_line, end_line,
            placeholder_prefix=placeholder_prefix
        )

    def should_strip_function_body(
        self,
        in_public_api: bool,
        lines_count: int,
    ) -> bool:
        """
        Determine if a function body should be stripped based on configuration.
        
        Args:
            in_public_api: A function or method is part of a public API
            lines_count: Number of lines in the function body

        Returns:
            True if body should be stripped, False otherwise
        """
        if isinstance(self.cfg, bool):
            # For boolean True, apply smart logic:
            # don't strip single-line bodies (important for arrow functions)
            # But allow override for complex config modes
            if self.cfg and lines_count <= 1:
                return False
            return self.cfg
        
        # If config is an object, apply complex logic
        complex_cfg: FunctionBodyConfig = cast(FunctionBodyConfig, self.cfg)
        mode = complex_cfg.mode

        if mode == "none":
            return False
        elif mode == "all":
            return True
        elif mode == "large_only":
            return lines_count >= complex_cfg.min_lines
        elif mode == "public_only":
            # Strip bodies only for public functions
            return in_public_api
        elif mode == "non_public":
            # Strip bodies only for private functions
            return not in_public_api

        return False

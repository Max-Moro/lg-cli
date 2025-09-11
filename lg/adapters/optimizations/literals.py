"""
Literal optimization.
Processes and trims literal data (strings, arrays, objects).
"""

from __future__ import annotations

from typing import Tuple, Optional, cast

from ..code_model import LiteralConfig
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class LiteralOptimizer:
    """Handles literal data processing optimization."""
    
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
        Apply literal processing based on configuration.
        
        Args:
            context: Processing context with document and editor
        """
        strip_config = self.adapter.cfg.strip_literals

        # Если отключено - ничего не делаем
        if not strip_config:
            return

        # Получаем конфигурацию
        if isinstance(strip_config, bool):
            # При strip_literals: true создаем конфиг с разумными дефолтами
            config = LiteralConfig(
                max_string_length=200,
                max_array_elements=20,
                max_object_properties=15,
                max_literal_lines=10,
                collapse_threshold=100
            )
        else:
            # Используем кастомную конфигурацию
            config = strip_config

        # Get all docstrings to exclude them from processing
        comments = context.doc.query("comments")
        docstring_nodes = {node for node, capture_name in comments if capture_name == "docstring"}

        # Get all literals from code
        literals = context.doc.query("literals")

        for node, capture_name in literals:
            # Skip docstrings - they should not be processed as literals
            if node in docstring_nodes:
                continue
                
            self._process_single_literal(node, capture_name, config, context)
    
    def _process_single_literal(
            self,
            node: Node,
            literal_type: str,
            config,
            context: ProcessingContext
    ) -> None:
        """
        Process a single literal for potential trimming.

        Args:
            node: Tree-sitter node with literal data
            literal_type: Type of literal (string, array, object)
            config: Literal processing configuration
            context: Processing context
        """
        node_text = context.doc.get_node_text(node)
        start_line, end_line = context.doc.get_line_range(node)
        lines_count = end_line - start_line + 1
        bytes_count = len(node_text.encode('utf-8'))

        should_trim = False
        replacement_text = None

        # Check different trimming conditions
        if literal_type == "string":
            should_trim, replacement_text = self._should_trim_string(
                node_text, config, bytes_count, context
            )
        elif literal_type == "array":
            should_trim, replacement_text = self._should_trim_array(
                node, node_text, config, lines_count, context
            )
        elif literal_type == "object":
            should_trim, replacement_text = self._should_trim_object(
                node, node_text, config, lines_count, context
            )

        # Check general conditions only if not already marked for trimming
        if not should_trim:
            if config.max_literal_lines is not None and lines_count > config.max_literal_lines:
                should_trim = True
                replacement_text = None  # Use auto placeholder
            elif config.collapse_threshold is not None and bytes_count > config.collapse_threshold:
                should_trim = True
                replacement_text = None  # Use auto placeholder

        if should_trim:
            if replacement_text is None:
                # Используем новое простое API для автоматических плейсхолдеров
                context.add_placeholder_for_node(literal_type, node)
            else:
                # Кастомная замена (например, укороченная строка)
                start_byte, end_byte = context.doc.get_node_range(node)
                context.editor.add_replacement(
                    start_byte, end_byte, replacement_text,
                    edit_type=f"{literal_type}_trimming",
                )
                context.metrics.mark_element_removed(literal_type)
    
    def _should_trim_string(
            self,
            text: str,
            config,
            byte_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if string literal should be trimmed.
        
        Args:
            text: String literal text
            config: Literal configuration
            byte_count: Actual byte count of string
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Remove quotes for analysis
        quote_char = text[0] if text and text[0] in ('"', "'", '`') else '"'
        inner_text = text.strip(quote_char)

        # Check collapse threshold first (если задан)
        if config.collapse_threshold is not None and byte_count > config.collapse_threshold:
            # Replace with comment placeholder (None means use auto placeholder)
            return True, None
        
        # Check max length (если задан)
        if config.max_string_length is not None and len(inner_text) > config.max_string_length:
            # Truncate to max length only for smaller strings
            truncated = inner_text[:config.max_string_length].rstrip()
            replacement = f'{quote_char}{truncated}...{quote_char}'
            return True, replacement

        return False, None
    
    def _should_trim_array(
            self,
            node: Node,
            text: str,
            config,
            lines_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if array literal should be trimmed.
        
        Args:
            node: Tree-sitter node for array
            text: Array literal text
            config: Literal configuration
            lines_count: Actual line count
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Count array elements through Tree-sitter
        elements_count = self._count_array_elements(node, context)

        # Check max elements (если задан)
        if config.max_array_elements is not None and elements_count > config.max_array_elements:
            # Use comment placeholder for arrays exceeding limits
            return True, None

        return False, None
    
    def _should_trim_object(
            self,
            node: Node,
            text: str,
            config,
            lines_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if object literal should be trimmed.
        
        Args:
            node: Tree-sitter node for object
            text: Object literal text
            config: Literal configuration
            lines_count: Actual line count
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Count object properties
        properties_count = self._count_object_properties(node, context)

        # Check max properties (если задан)
        if config.max_object_properties is not None and properties_count > config.max_object_properties:
            # Use comment placeholder for objects exceeding limits
            return True, None

        return False, None
    
    def _count_array_elements(self, node: Node, context: ProcessingContext) -> int:
        """Count elements in array through Tree-sitter."""
        elements = 0
        for child in node.children:
            if child.type not in ('[', ']', ','):  # Skip syntax symbols
                elements += 1
        return elements
    
    def _count_object_properties(self, node: Node, context: ProcessingContext) -> int:
        """Count properties in object through Tree-sitter."""
        properties = 0
        for child in node.children:
            # Look for pair, property, or similar nodes
            if 'pair' in child.type or 'property' in child.type:
                properties += 1
        return properties
    
    

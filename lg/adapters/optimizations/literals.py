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
            # Используем дефолтные настройки при strip_literals: true
            config = LiteralConfig()
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
                node_text, config.max_string_length, config.collapse_threshold, bytes_count, context
            )
        elif literal_type == "array":
            should_trim, replacement_text = self._should_trim_array(
                node, node_text, config.max_array_elements, config.max_literal_lines, lines_count, context
            )
        elif literal_type == "object":
            should_trim, replacement_text = self._should_trim_object(
                node, node_text, config.max_object_properties, config.max_literal_lines, lines_count, context
            )

        # Check general conditions
        if not should_trim:
            if lines_count > config.max_literal_lines:
                should_trim = True
                replacement_text = context.placeholder_gen.create_literal_placeholder(
                    literal_type, bytes_count, style="inline"
                )
            elif bytes_count > config.collapse_threshold:
                should_trim = True
                replacement_text = context.placeholder_gen.create_literal_placeholder(
                    literal_type, bytes_count, style="inline"
                )

        if should_trim and replacement_text:
            start_byte, end_byte = context.doc.get_node_range(node)

            context.editor.add_replacement(
                start_byte, end_byte, replacement_text,
                type=f"{literal_type}_trimming",
                is_placeholder=True,
                lines_removed=lines_count
            )

            context.metrics.mark_literal_removed()
            context.metrics.add_lines_saved(lines_count)
            context.metrics.add_bytes_saved(bytes_count - len(replacement_text.encode('utf-8')))
            context.metrics.mark_placeholder_inserted()
    
    def _should_trim_string(
            self,
            text: str,
            max_length: int,
            collapse_threshold: int,
            byte_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if string literal should be trimmed.
        
        Args:
            text: String literal text
            max_length: Maximum allowed string length
            collapse_threshold: Byte threshold for collapsing
            byte_count: Actual byte count of string
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Remove quotes for analysis
        quote_char = text[0] if text and text[0] in ('"', "'", '`') else '"'
        inner_text = text.strip(quote_char)

        # Prioritize collapse over truncation for large data
        if byte_count > collapse_threshold:
            # Replace with comment placeholder
            replacement = context.placeholder_gen.create_literal_placeholder(
                "string", byte_count, style="inline"
            )
            return True, replacement
        elif len(inner_text) > max_length:
            # Truncate to max length only for smaller strings
            truncated = inner_text[:max_length].rstrip()
            replacement = f'{quote_char}{truncated}...{quote_char}'
            return True, replacement

        return False, None
    
    def _should_trim_array(
            self,
            node: Node,
            text: str,
            max_elements: int,
            max_lines: int,
            lines_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if array literal should be trimmed.
        
        Args:
            node: Tree-sitter node for array
            text: Array literal text
            max_elements: Maximum number of elements to show
            max_lines: Maximum lines before collapsing
            lines_count: Actual line count
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Count array elements through Tree-sitter
        elements_count = self._count_array_elements(node, context)

        if elements_count > max_elements or lines_count > max_lines:
            # Use comment placeholder for arrays exceeding limits
            replacement = context.placeholder_gen.create_literal_placeholder(
                "array", len(text.encode('utf-8')), style="inline"
            )
            return True, replacement

        return False, None
    
    def _should_trim_object(
            self,
            node: Node,
            text: str,
            max_properties: int,
            max_lines: int,
            lines_count: int,
            context: ProcessingContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if object literal should be trimmed.
        
        Args:
            node: Tree-sitter node for object
            text: Object literal text
            max_properties: Maximum number of properties to show
            max_lines: Maximum lines before collapsing
            lines_count: Actual line count
            context: Processing context
            
        Returns:
            Tuple of (should_trim, replacement_text)
        """
        # Count object properties
        properties_count = self._count_object_properties(node, context)

        if properties_count > max_properties or lines_count > max_lines:
            # Use comment placeholder for objects exceeding limits
            replacement = context.placeholder_gen.create_literal_placeholder(
                "object", len(text.encode('utf-8')), style="inline"
            )
            return True, replacement

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
    
    

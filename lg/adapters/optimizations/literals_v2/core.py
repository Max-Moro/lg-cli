"""
Core literal optimizer v2.

Main entry point for the literal optimization system.
Integrates with the existing adapter infrastructure.
"""

from __future__ import annotations

from typing import cast, Optional

from .categories import TrimResult
from .handler import LanguageLiteralHandler
from ...code_model import LiteralConfig
from ...context import ProcessingContext
from tree_sitter import Node


class LiteralOptimizerV2:
    """
    Literal optimizer using the v2 architecture.

    Created per-adapter, similar to other optimizers.
    """

    def __init__(self, cfg: LiteralConfig, adapter):
        """
        Initialize the optimizer.

        Args:
            cfg: LiteralConfig with max_tokens setting
            adapter: Language adapter (for descriptor, comment style, tokenizer)
        """
        self.cfg = cfg
        from ...code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)

        # Get descriptor from adapter
        descriptor = self.adapter.create_literal_descriptor()
        if descriptor is None:
            self.handler: Optional[LanguageLiteralHandler] = None
            return

        # Create handler with language-specific comment style
        comment_style = self.adapter.get_comment_style()
        self.handler = LanguageLiteralHandler(
            self.adapter.name,
            descriptor,
            self.adapter.tokenizer,
            (comment_style[0], (comment_style[1][0], comment_style[1][1]))
        )

    def apply(self, context: ProcessingContext) -> None:
        """
        Apply literal optimization to a processing context.

        Args:
            context: Processing context with document
        """
        if self.handler is None:
            return  # Language not supported by v2

        # Get max_tokens from config
        max_tokens = self.cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Query for all literals
        literals = list(context.doc.query("literals"))

        # Two-pass approach for orthogonal string/collection processing.

        # Pass 0: Identify collections
        collections = [
            (node, capture_name)
            for node, capture_name in literals
            if capture_name != "string"
        ]

        processed_strings = []  # Track (start, end, tokens_saved) for processed strings

        # Pass 1: Strings (all strings, processed independently)
        for node, capture_name in literals:
            if capture_name != "string":
                continue

            # Skip docstrings
            if self.adapter.is_docstring_node(node, context.doc):
                continue

            # Get node info
            literal_text = context.doc.get_node_text(node)
            token_count = self.adapter.tokenizer.count_text(literal_text)

            # Skip if within budget
            if token_count <= max_tokens:
                continue

            # Process
            result = self._process_node(context, node, max_tokens)
            if result and result.saved_tokens > 0:
                start_byte, end_byte = context.doc.get_node_range(node)
                self._apply_trim_result(context, node, result, literal_text)
                tokens_saved = result.saved_tokens
                processed_strings.append((start_byte, end_byte, tokens_saved))

        # Pass 2: Collections (arrays, objects, etc.)
        # Process only top-level collections (not nested inside other collections)
        # DFS will handle nested structures internally

        # Find top-level collections (not contained by other collections)
        top_level = []
        for i, (node, capture_name) in enumerate(collections):
            start_byte, end_byte = context.doc.get_node_range(node)
            is_nested = any(
                j != i and
                collections[j][0].start_byte <= start_byte and
                collections[j][0].end_byte >= end_byte
                for j in range(len(collections))
            )
            if not is_nested:
                # Skip if contained in a processed string range
                contained_in_processed_string = any(
                    s <= start_byte and end_byte <= e
                    for s, e, _ in processed_strings
                )
                if not contained_in_processed_string:
                    top_level.append((node, capture_name))

        for node, capture_name in top_level:
            literal_text = context.doc.get_node_text(node)
            token_count = self.adapter.tokenizer.count_text(literal_text)

            # Skip if within budget
            if token_count <= max_tokens:
                continue

            # Process with DFS (will handle nested structures internally)
            result = self._process_node(context, node, max_tokens)

            # Apply if any tokens were saved (removals can be in nested levels only)
            if result and result.saved_tokens > 0:
                # Apply using composing method - this will preserve nested string edits
                self._apply_trim_result_composing(context, node, result, literal_text)

    def _apply_trim_result(
        self,
        context: ProcessingContext,
        node: Node,
        result: TrimResult,
        original_text: str
    ) -> None:
        """Apply trim result to context (replacement + comment + metrics)."""
        start_byte, end_byte = context.doc.get_node_range(node)

        # Apply replacement
        context.editor.add_replacement(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        # Add comment if needed
        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            # Get text after literal for context-aware comment formatting
            text_after = context.raw_text[end_byte:]

            # Use handler to determine comment format and position
            formatted_comment, offset = self.handler.get_comment_for_context(
                text_after, result.comment_text
            )

            # Insert at calculated position (end_byte + offset)
            context.editor.add_insertion(
                end_byte + offset,
                formatted_comment,
                edit_type="literal_comment"
            )

        # Update metrics
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))

    def _apply_trim_result_composing(
        self,
        context: ProcessingContext,
        node: Node,
        result: TrimResult,
        original_text: str
    ) -> None:
        """
        Apply trim result using composing method.

        This preserves nested narrow edits (from Pass 1) by composing them
        with the wide edit (from Pass 2 DFS).
        """
        start_byte, end_byte = context.doc.get_node_range(node)

        # Apply replacement using composing method
        # This will find and preserve any nested string edits from Pass 1
        context.editor.add_replacement_composing_nested(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        # Add comment if needed
        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            # Get text after literal for context-aware comment formatting
            text_after = context.raw_text[end_byte:]

            # Use handler to determine comment format and position
            formatted_comment, offset = self.handler.get_comment_for_context(
                text_after, result.comment_text
            )

            # Insert at calculated position (end_byte + offset)
            context.editor.add_insertion(
                end_byte + offset,
                formatted_comment,
                edit_type="literal_comment"
            )

        # Update metrics
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))

    def _process_node(
        self,
        context: ProcessingContext,
        node: Node,
        max_tokens: int,
    ) -> Optional[TrimResult]:
        """
        Process a single tree-sitter node for literal optimization.

        Args:
            context: Processing context with file info
            node: Tree-sitter node to process
            max_tokens: Token budget for this literal

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        if self.handler is None:
            return None

        # Check if this node type is a literal
        if not self.handler.detect_literal_type(node.type):
            return None

        # Get node text and position
        text = context.doc.get_node_text(node)
        start_byte, end_byte = context.doc.get_node_range(node)

        # Detect indentation
        base_indent = self._get_base_indent(context.raw_text, start_byte)
        element_indent = self._get_element_indent(text, base_indent)

        # Process through handler
        return self.handler.process_literal(
            text=text,
            tree_sitter_type=node.type,
            start_byte=start_byte,
            end_byte=end_byte,
            token_budget=max_tokens,
            base_indent=base_indent,
            element_indent=element_indent,
        )

    def _get_base_indent(self, text: str, byte_pos: int) -> str:
        """Get indentation of line containing byte position."""
        # Find line start
        line_start = text.rfind('\n', 0, byte_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        # Extract indent
        indent = ""
        for i in range(line_start, min(byte_pos, len(text))):
            if text[i] in ' \t':
                indent += text[i]
            else:
                break

        return indent

    def _get_element_indent(self, literal_text: str, base_indent: str) -> str:
        """Detect element indentation from literal content."""
        lines = literal_text.split('\n')
        if len(lines) < 2:
            return base_indent + "    "

        # Look at second line for element indentation
        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith((']', '}', ')')):
                # Extract this line's indentation
                indent = ""
                for char in line:
                    if char in ' \t':
                        indent += char
                    else:
                        break
                if indent:
                    return indent

        return base_indent + "    "

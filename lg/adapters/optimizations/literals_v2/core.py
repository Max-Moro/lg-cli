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
        literals = context.doc.query("literals")

        for node, capture_name in literals:
            # Skip docstrings
            if capture_name == "string" and self.adapter.is_docstring_node(node, context.doc):
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
                # Apply replacement
                start_byte, end_byte = context.doc.get_node_range(node)
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
                context.metrics.add_chars_saved(len(literal_text) - len(result.trimmed_text))

    def _process_node(
        self,
        context: ProcessingContext,
        node: "Node",
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

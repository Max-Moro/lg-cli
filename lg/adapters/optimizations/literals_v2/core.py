"""
Core literal optimizer v2.

Main entry point for the literal optimization system.
Integrates with the existing adapter infrastructure.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .categories import TrimResult
from .descriptor import LanguageLiteralDescriptor
from .handler import LanguageLiteralHandler
from lg.stats.tokenizer import TokenService


def get_descriptor_for_language(language: str) -> Optional[LanguageLiteralDescriptor]:
    """
    Get language descriptor by language name.

    Lazy-loads descriptors to avoid circular imports.
    """
    if language == "python":
        from lg.adapters.python.literals_v2 import PYTHON_DESCRIPTOR
        return PYTHON_DESCRIPTOR
    elif language == "javascript":
        from lg.adapters.javascript.literals_v2 import JAVASCRIPT_DESCRIPTOR
        return JAVASCRIPT_DESCRIPTOR
    elif language == "typescript":
        from lg.adapters.typescript.literals_v2 import TYPESCRIPT_DESCRIPTOR
        return TYPESCRIPT_DESCRIPTOR
    # Languages not yet migrated to v2
    return None


class LiteralOptimizerV2:
    """
    Universal literal optimizer using the v2 architecture.

    Designed to integrate with the existing code adapter system.
    Manages language handlers and coordinates optimization.
    """

    def __init__(self, tokenizer: TokenService):
        """
        Initialize the optimizer.

        Args:
            tokenizer: TokenService for token counting
        """
        self.tokenizer = tokenizer
        self._handlers: Dict[str, LanguageLiteralHandler] = {}
        self._descriptors: Dict[str, LanguageLiteralDescriptor] = {}

    def register_descriptor(
        self,
        descriptor: LanguageLiteralDescriptor,
        comment_style: tuple[str, tuple[str, str]] = ("//", ("/*", "*/")),
    ) -> None:
        """
        Register a language descriptor and create its handler.

        Args:
            descriptor: Language literal descriptor
            comment_style: Comment syntax for this language
        """
        self._descriptors[descriptor.language] = descriptor
        self._handlers[descriptor.language] = LanguageLiteralHandler(
            descriptor, self.tokenizer, comment_style
        )

    def get_handler(self, language: str) -> Optional[LanguageLiteralHandler]:
        """Get handler for a language."""
        return self._handlers.get(language)

    def apply(self, context: "ProcessingContext", adapter) -> None:
        """
        Apply literal optimization to a processing context.

        Compatible interface with old LiteralOptimizer.

        Args:
            context: Processing context with document
            adapter: Language adapter (for comment style, config)
        """
        from lg.adapters.context import ProcessingContext

        # Get config from adapter
        max_tokens = adapter.cfg.literals.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Get language from adapter
        language = adapter.name

        # Auto-register descriptor if not already registered
        if language not in self._handlers:
            descriptor = get_descriptor_for_language(language)
            if descriptor is None:
                # Language not supported by v2 yet, skip
                return
            comment_style = adapter.get_comment_style()
            self.register_descriptor(descriptor, (comment_style[0], (comment_style[1][0], comment_style[1][1])))

        # Get handler
        handler = self._handlers.get(language)
        if not handler:
            return

        # Query for all literals
        literals = context.doc.query("literals")

        for node, capture_name in literals:
            # Skip docstrings
            if capture_name == "string" and adapter.is_docstring_node(node, context.doc):
                continue

            # Get node info
            literal_text = context.doc.get_node_text(node)
            token_count = self.tokenizer.count_text(literal_text)

            # Skip if within budget
            if token_count <= max_tokens:
                continue

            # Process
            result = self.process_node(context, node, max_tokens, language)
            if result and result.saved_tokens > 0:
                # Apply replacement
                start_byte, end_byte = context.doc.get_node_range(node)
                context.editor.add_replacement(
                    start_byte, end_byte, result.trimmed_text,
                    edit_type="literal_trimmed"
                )

                # Add comment if needed
                placeholder_style = adapter.cfg.placeholders.style
                if placeholder_style != "none" and result.comment_text:
                    # Get text after literal for context-aware comment formatting
                    text_after = context.raw_text[end_byte:]

                    # Use handler to determine comment format and position
                    formatted_comment, offset = handler.get_comment_for_context(
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

    def process_node(
        self,
        context: "ProcessingContext",
        node: "Node",
        max_tokens: int,
        language: str,
    ) -> Optional[TrimResult]:
        """
        Process a single tree-sitter node for literal optimization.

        This is the main integration point with the existing adapter system.

        Args:
            context: Processing context with file info
            node: Tree-sitter node to process
            max_tokens: Token budget for this literal
            language: Language name for handler lookup

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        from lg.adapters.context import ProcessingContext
        from lg.adapters.tree_sitter_support import Node

        # Get handler for this language
        handler = self._handlers.get(language)
        if not handler:
            return None

        # Check if this node type is a literal
        if not handler.detect_literal_type(node.type):
            return None

        # Get node text and position
        text = context.doc.get_node_text(node)
        start_byte, end_byte = context.doc.get_node_range(node)

        # Detect indentation
        base_indent = self._get_base_indent(context.raw_text, start_byte)
        element_indent = self._get_element_indent(text, base_indent)

        # Process through handler
        return handler.process_literal(
            text=text,
            tree_sitter_type=node.type,
            start_byte=start_byte,
            end_byte=end_byte,
            token_budget=max_tokens,
            base_indent=base_indent,
            element_indent=element_indent,
        )

    def apply_to_context(
        self,
        context: "ProcessingContext",
        max_tokens: int,
        language: str,
        query_name: str = "literals",
    ) -> List[TrimResult]:
        """
        Apply literal optimization to all literals in a processing context.

        Args:
            context: Processing context
            max_tokens: Token budget per literal
            language: Language name for handler lookup
            query_name: Tree-sitter query name for finding literals

        Returns:
            List of TrimResult for applied optimizations
        """
        from lg.adapters.context import ProcessingContext

        results = []

        # Get handler for this file's language
        handler = self._handlers.get(language)
        if not handler:
            return results

        # Query for all literals
        literals = context.doc.query(query_name)

        for node, capture_name in literals:
            # Skip if not a literal type we handle
            if not handler.detect_literal_type(node.type):
                continue

            # Get node info
            text = context.doc.get_node_text(node)
            token_count = self.tokenizer.count_text(text)

            # Skip if within budget
            if token_count <= max_tokens:
                continue

            # Process
            result = self.process_node(context, node, max_tokens, language)
            if result and result.saved_tokens > 0:
                results.append(result)

                # Apply to context editor
                context.editor.add_replacement(
                    result.trimmed_text,
                    node.start_byte,
                    node.end_byte,
                    edit_type="literal_trimmed"
                )

                # Add comment if needed
                if result.comment_text and result.comment_position:
                    context.editor.add_insertion(
                        result.comment_position,
                        result.comment_text,
                        edit_type="literal_comment"
                    )

        return results

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


def create_optimizer(tokenizer: TokenService) -> LiteralOptimizerV2:
    """
    Create a LiteralOptimizerV2 instance.

    Args:
        tokenizer: Token counting service

    Returns:
        Configured optimizer (without language handlers)
    """
    return LiteralOptimizerV2(tokenizer)

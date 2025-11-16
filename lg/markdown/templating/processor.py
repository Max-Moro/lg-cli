"""
Processor for handling Markdown with conditional constructs.

Combines lexer, parser, and condition evaluator for complete processing
of Markdown documents with LG instructions in HTML comments.
"""

from __future__ import annotations

from typing import Tuple, Optional

from .nodes import (
    MarkdownAST, MarkdownNode, TextNode, ConditionalBlockNode,
    CommentBlockNode, RawBlockNode
)
from .parser import parse_markdown_template, MarkdownTemplateParserError


class MarkdownTemplateProcessorError(Exception):
    """Error in processing Markdown with conditional constructs."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class MarkdownTemplateProcessor:
    """
    Processor for Markdown with conditional constructs.

    Performs complete processing cycle: lexical analysis, parsing,
    condition evaluation, and final text generation.
    """

    def __init__(self, template_ctx=None):
        """
        Initialize processor.

        Args:
            template_ctx: Template context for condition evaluation (optional)
        """
        self.template_ctx = template_ctx

    def process(self, text: str) -> Tuple[str, dict]:
        """
        Process Markdown text with conditional constructs.

        Args:
            text: Source Markdown text

        Returns:
            Tuple (processed_text, metadata)

        Raises:
            MarkdownTemplateProcessorError: On processing error
        """
        try:
            # 1. Parse text into AST
            ast = parse_markdown_template(text)

            # 2. Evaluate conditions and generate result
            processed_text = self._evaluate_ast(ast)

            # 3. Collect metadata
            meta = self._collect_metadata(ast)

            return processed_text, meta

        except MarkdownTemplateParserError as e:
            raise MarkdownTemplateProcessorError(f"Parsing error: {e}", e)
        except Exception as e:
            raise MarkdownTemplateProcessorError(f"Unexpected processing error: {e}", e)
    
    def _evaluate_ast(self, ast: MarkdownAST) -> str:
        """
        Evaluate AST and generate final text.

        Args:
            ast: AST to evaluate

        Returns:
            Final processed text
        """
        result_parts = []

        for node in ast:
            result_parts.append(self._evaluate_node(node))

        return "".join(result_parts)

    def _evaluate_node(self, node: MarkdownNode) -> str:
        """
        Evaluate single AST node.

        Args:
            node: Node to evaluate

        Returns:
            Text representation of node
        """
        if isinstance(node, TextNode):
            return node.text

        elif isinstance(node, ConditionalBlockNode):
            return self._evaluate_conditional_block(node)

        elif isinstance(node, CommentBlockNode):
            # Comments are removed during processing
            return ""

        elif isinstance(node, RawBlockNode):
            # Raw blocks output as-is without processing
            return node.text

        else:
            # Unknown node type - return as-is
            return f"<!-- Unknown node type: {type(node).__name__} -->"
    
    def _evaluate_conditional_block(self, node: ConditionalBlockNode) -> str:
        """
        Evaluate conditional block.

        Args:
            node: Conditional block node

        Returns:
            Text of matching condition branch or empty string
        """
        # Evaluate main condition
        if self._evaluate_condition(node.condition_text):
            return self._evaluate_ast(node.body)

        # Check elif blocks in order
        if node.elif_blocks:
            for elif_block in node.elif_blocks:
                if self._evaluate_condition(elif_block.condition_text):
                    return self._evaluate_ast(elif_block.body)

        # If no condition matched, check else block
        if node.else_block:
            return self._evaluate_ast(node.else_block.body)

        return ""
    
    def _evaluate_condition(self, condition_text: str) -> bool:
        """
        Evaluate text condition.

        Args:
            condition_text: Condition text to evaluate

        Returns:
            Result of condition evaluation
        """
        if not condition_text:
            return False

        if self.template_ctx is None:
            # If template context not set, return False for all conditions
            return False

        try:
            # Use condition evaluator from template context
            return self.template_ctx.evaluate_condition_text(condition_text)
        except Exception:
            # On condition evaluation error, return False
            return False

    def _collect_metadata(self, ast: MarkdownAST) -> dict:
        """
        Collect processing metadata.

        Args:
            ast: AST to analyze

        Returns:
            Metadata dictionary
        """
        meta = {
            "md.templating.processed": True,
            "md.templating.conditional_blocks": 0,
            "md.templating.comment_blocks": 0,
            "md.templating.conditions_evaluated": 0,
            "md.templating.conditions_true": 0
        }

        def analyze_node(node: MarkdownNode) -> None:
            if isinstance(node, ConditionalBlockNode):
                meta["md.templating.conditional_blocks"] += 1

                # Analyze main condition
                if node.condition_text:
                    meta["md.templating.conditions_evaluated"] += 1
                    if self._evaluate_condition(node.condition_text):
                        meta["md.templating.conditions_true"] += 1

                # Analyze elif conditions
                if node.elif_blocks:
                    for elif_block in node.elif_blocks:
                        if elif_block.condition_text:
                            meta["md.templating.conditions_evaluated"] += 1
                            if self._evaluate_condition(elif_block.condition_text):
                                meta["md.templating.conditions_true"] += 1

                # Recursively analyze content
                for child in node.body:
                    analyze_node(child)
                if node.elif_blocks:
                    for elif_block in node.elif_blocks:
                        for child in elif_block.body:
                            analyze_node(child)
                if node.else_block:
                    for child in node.else_block.body:
                        analyze_node(child)

            elif isinstance(node, CommentBlockNode):
                meta["md.templating.comment_blocks"] += 1

            elif isinstance(node, RawBlockNode):
                # Raw blocks not counted separately, but can add metric if needed
                pass

        for node in ast:
            analyze_node(node)

        return meta


def process_markdown_template(text: str, template_ctx=None) -> Tuple[str, dict]:
    """
    Convenience function for processing Markdown with conditional constructs.

    Args:
        text: Source Markdown text
        template_ctx: Template context for condition evaluation (optional)

    Returns:
        Tuple (processed_text, metadata)

    Raises:
        MarkdownTemplateProcessorError: On processing error
    """
    processor = MarkdownTemplateProcessor(template_ctx)
    return processor.process(text)


__all__ = [
    "MarkdownTemplateProcessor",
    "MarkdownTemplateProcessorError", 
    "process_markdown_template"
]
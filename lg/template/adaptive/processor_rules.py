"""
Processing rules for adaptive constructs in templates.

Handles conditional blocks, mode blocks, and comments.
"""

from __future__ import annotations

from typing import Callable, List

from .nodes import ConditionalBlockNode, ModeBlockNode, CommentNode
from ..types import ProcessorRule, ProcessingContext
from ...template.context import TemplateContext

# Callable type for AST node processing
ProcessASTNodeFunc = Callable[[ProcessingContext], str]


class AdaptiveProcessorRules:
    """
    Processing rules class for adaptive constructs.

    Encapsulates all processing rules with access to the
    AST node processing functor through instance state.
    """

    def __init__(self, process_ast_node: ProcessASTNodeFunc, template_ctx: TemplateContext):
        """
        Initializes processing rules.

        Args:
            process_ast_node: Functor for processing AST nodes
            template_ctx: Template context for state management
        """
        self.process_ast_node = process_ast_node
        self.template_ctx = template_ctx

    def process_conditional(self, processing_context: ProcessingContext) -> str:
        """
        Processes a conditional block {% if ... %}.

        Evaluates the condition and returns appropriate content.
        """
        node = processing_context.get_node()
        if not isinstance(node, ConditionalBlockNode):
            raise RuntimeError(f"Expected ConditionalBlockNode, got {type(node)}")

        # Evaluate main condition
        if node.condition_ast:
            condition_result = self.template_ctx.evaluate_condition(node.condition_ast)
        else:
            # Fallback to text evaluation
            condition_result = self.template_ctx.evaluate_condition_text(node.condition_text)

        # If main condition is true, render if body
        if condition_result:
            return self._render_body(node.body)

        # Check elif blocks
        for elif_block in node.elif_blocks:
            if elif_block.condition_ast:
                elif_result = self.template_ctx.evaluate_condition(elif_block.condition_ast)
            else:
                elif_result = self.template_ctx.evaluate_condition_text(elif_block.condition_text)

            if elif_result:
                return self._render_body(elif_block.body)

        # If all conditions are false, render else block if it exists
        if node.else_block:
            return self._render_body(node.else_block.body)

        # All conditions false and no else - return empty string
        return ""

    def process_mode_block(self, processing_context: ProcessingContext) -> str:
        """
        Processes a mode block {% mode ... %}.

        Switches mode and processes block body with new mode.
        """
        node = processing_context.get_node()
        if not isinstance(node, ModeBlockNode):
            raise RuntimeError(f"Expected ModeBlockNode, got {type(node)}")

        # Enter mode block
        self.template_ctx.enter_mode_block(node.modeset, node.mode)

        try:
            # Render block body with active mode
            result = self._render_body(node.body)
        finally:
            # Always exit block, even on error
            self.template_ctx.exit_mode_block()

        return result

    def process_comment(self, processing_context: ProcessingContext) -> str:
        """
        Processes a comment {# ... #}.

        Comments do not appear in output.
        """
        node = processing_context.get_node()
        if not isinstance(node, CommentNode):
            raise RuntimeError(f"Expected CommentNode, got {type(node)}")

        # Comments are ignored during rendering
        return ""

    def _render_body(self, body: list) -> str:
        """
        Renders a list of nodes in block body.

        Args:
            body: List of nodes to render

        Returns:
            Rendered content
        """
        result_parts = []

        for i, child_node in enumerate(body):
            # Create processing context for each node
            processing_context = ProcessingContext(ast=body, node_index=i)
            rendered = self.process_ast_node(processing_context)
            if rendered:
                result_parts.append(rendered)

        return "".join(result_parts)


def get_adaptive_processor_rules(
    process_ast_node: ProcessASTNodeFunc,
    template_ctx: TemplateContext
) -> List[ProcessorRule]:
    """
    Returns processing rules for adaptive constructs.

    Args:
        process_ast_node: Functor for processing AST nodes
        template_ctx: Template context for state management

    Returns:
        List of processing rules with bound functors
    """
    rules_instance = AdaptiveProcessorRules(process_ast_node, template_ctx)

    return [
        ProcessorRule(
            node_type=ConditionalBlockNode,
            processor_func=rules_instance.process_conditional
        ),
        ProcessorRule(
            node_type=ModeBlockNode,
            processor_func=rules_instance.process_mode_block
        ),
        ProcessorRule(
            node_type=CommentNode,
            processor_func=rules_instance.process_comment
        ),
        # ElifBlockNode is not processed separately - it's part of ConditionalBlockNode
    ]


__all__ = ["AdaptiveProcessorRules", "ProcessASTNodeFunc", "get_adaptive_processor_rules"]

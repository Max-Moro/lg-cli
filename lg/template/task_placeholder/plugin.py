"""
Plugin for processing task placeholders.
"""

from __future__ import annotations

from typing import List

from .nodes import TaskNode
from .parser_rules import get_task_parser_rules
from .tokens import get_task_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ProcessingContext
from ...template import TemplateContext


class TaskPlaceholderPlugin(TemplatePlugin):
    """
    Plugin for processing task placeholders.

    Provides functionality:
    - ${task} - simple task text insertion
    - ${task:prompt:"default text"} - insertion with default value
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Initializes plugin with template context.

        Args:
            template_ctx: Template context for state management
        """
        super().__init__()
        self.template_ctx = template_ctx

    @property
    def name(self) -> str:
        """Returns plugin name."""
        return "task_placeholder"

    @property
    def priority(self) -> PluginPriority:
        """Returns plugin priority."""
        return PluginPriority.PLACEHOLDER

    def initialize(self) -> None:
        """Adds task-specific tokens to placeholder context."""
        # Add only STRING_LITERAL since task/prompt are checked via IDENTIFIER
        self.registry.register_tokens_in_context(
            "placeholder",
            ["STRING_LITERAL"]
        )

    def register_tokens(self) -> List[TokenSpec]:
        """Registers tokens for task placeholders."""
        return get_task_token_specs()

    def register_parser_rules(self) -> List[ParsingRule]:
        """Registers parsing rules for task placeholders."""
        return get_task_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Registers AST node handlers.
        """
        def process_task_node(processing_context: ProcessingContext) -> str:
            """Processes TaskNode."""
            node = processing_context.get_node()
            if not isinstance(node, TaskNode):
                raise RuntimeError(f"Expected TaskNode, got {type(node)}")

            # Get effective task text (considering modes)
            effective_task_text = self.template_ctx.run_ctx.get_effective_task_text()

            # If effective task_text exists - return it
            if effective_task_text:
                return effective_task_text

            # If no effective task and default_prompt exists - return it
            if node.default_prompt is not None:
                return node.default_prompt

            # Otherwise return empty string
            return ""

        return [
            ProcessorRule(
                node_type=TaskNode,
                processor_func=process_task_node
            )
        ]


__all__ = ["TaskPlaceholderPlugin"]
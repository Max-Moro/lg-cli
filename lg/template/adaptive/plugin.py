"""
Plugin for adaptive template features.

Registers all necessary tokens, parsing rules, and handlers
for supporting conditional blocks, mode blocks, and comments.
"""

from __future__ import annotations

from typing import List

from .parser_rules import get_adaptive_parser_rules
from .processor_rules import get_adaptive_processor_rules
from .tokens import get_adaptive_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, TokenContext
from ...template.context import TemplateContext


class AdaptivePlugin(TemplatePlugin):
    """
    Plugin for adaptive template features.

    Provides functionality:
    - {% if condition %}...{% elif %}...{% else %}...{% endif %} - conditional blocks
    - {% mode modeset:mode %}...{% endmode %} - mode blocks
    - {# comment #} - comments
    - Logical operators AND, OR, NOT
    - Condition operators: tag:name, TAGSET:set:tag, scope:local
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
        return "adaptive"

    @property
    def priority(self) -> PluginPriority:
        """Returns plugin priority."""
        return PluginPriority.DIRECTIVE

    def register_tokens(self) -> List[TokenSpec]:
        """Registers tokens for adaptive constructs."""
        return get_adaptive_token_specs()

    def register_token_contexts(self) -> List[TokenContext]:
        """Registers token contexts for adaptive constructs."""
        return [
            TokenContext(
                name="directive",
                open_tokens={"DIRECTIVE_START"},
                close_tokens={"DIRECTIVE_END"},
                inner_tokens={
                    "IDENTIFIER", "COLON", "LPAREN", "RPAREN", "WHITESPACE"
                },
                allow_nesting=False,
            ),
            TokenContext(
                name="comment",
                open_tokens={"COMMENT_START"},
                close_tokens={"COMMENT_END"},
                inner_tokens=set(),  # Inside comment, everything is text
                allow_nesting=False,
            )
        ]

    def register_parser_rules(self) -> List[ParsingRule]:
        """
        Registers parsing rules for adaptive constructs.

        Uses closure for lazy access to handlers.parse_next_node.
        """
        return get_adaptive_parser_rules(lambda ctx: self.handlers.parse_next_node(ctx))

    def register_processors(self) -> List[ProcessorRule]:
        """
        Registers AST node handlers.

        Uses closures for lazy access to handlers.
        """
        return get_adaptive_processor_rules(
            process_ast_node=lambda ctx: self.handlers.process_ast_node(ctx),
            template_ctx=self.template_ctx
        )


__all__ = ["AdaptivePlugin"]


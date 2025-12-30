"""
Plugin for processing basic section and template placeholders.

Registers all necessary tokens, parsing rules, and handlers
for supporting ${section}, ${tpl:name}, ${ctx:name} and addressed references.
"""

from __future__ import annotations

from typing import List

from .nodes import SectionNode, IncludeNode
from .parser_rules import get_placeholder_parser_rules
from .tokens import get_placeholder_token_specs
from ..base import TemplatePlugin
from ..nodes import TemplateNode
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenContext, ProcessingContext
from ...template import TemplateContext


class CommonPlaceholdersPlugin(TemplatePlugin):
    """
    Plugin for processing basic section and template placeholders.

    Provides functionality:
    - ${section_name} - section insertion
    - ${tpl:template_name} - template inclusion
    - ${ctx:context_name} - context inclusion
    - Addressed references @origin:name for cross-scope inclusions
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Initializes plugin with template context.

        Args:
            template_ctx: Template context for state management
        """
        super().__init__()
        self.template_ctx = template_ctx
        # Resolver will be created once during initialization
        self._resolver = None

    @property
    def name(self) -> str:
        """Returns plugin name."""
        return "common_placeholders"

    @property
    def priority(self) -> PluginPriority:
        """Returns plugin priority."""
        return PluginPriority.PLACEHOLDER

    def initialize(self) -> None:
        """Initializes resolver after all dependencies are set."""
        from .resolver import CommonPlaceholdersResolver
        # Create resolver with all dependencies
        self._resolver = CommonPlaceholdersResolver(
            self.handlers,
            self.registry,
            self.template_ctx
        )
    
    def register_tokens(self) -> List[TokenSpec]:
        """Registers tokens for placeholders."""
        return get_placeholder_token_specs()

    def register_token_contexts(self) -> List[TokenContext]:
        """Registers token contexts for placeholders."""
        return [TokenContext(
            name="placeholder",
            open_tokens={"PLACEHOLDER_START"},
            close_tokens={"PLACEHOLDER_END"},
            inner_tokens={
                "IDENTIFIER", "COLON", "AT", "LBRACKET", "RBRACKET", "WHITESPACE"
            },
            allow_nesting=False,
        )]

    def register_parser_rules(self) -> List[ParsingRule]:
        """Registers placeholder parsing rules."""
        return get_placeholder_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Registers AST node handlers.

        Creates closures over typed handlers for direct node processing.
        """
        def process_section_node(processing_context: ProcessingContext) -> str:
            """Processes section node through typed handlers."""
            node = processing_context.get_node()
            if not isinstance(node, SectionNode):
                raise RuntimeError(f"Expected SectionNode, got {type(node)}")

            # Use typed section handler (resolved_ref is always present after resolution)
            return self.handlers.process_section_ref(node.resolved_ref)

        def process_include_node(processing_context: ProcessingContext) -> str:
            """Processes include node through typed handlers."""
            node = processing_context.get_node()
            if not isinstance(node, IncludeNode):
                raise RuntimeError(f"Expected IncludeNode, got {type(node)}")

            # Check that include was loaded
            if node.children is None:
                raise RuntimeError(f"Include '{node.canon_key()}' not resolved")

            # Render child nodes with file scope context for nested AST
            # This ensures that relative paths in nested templates resolve correctly
            result_parts = []
            scope_rel = None if node.origin == "self" else node.origin
            with self.template_ctx.file_scope(node.resolved_path, scope_rel):
                for child_index, child_node in enumerate(node.children):
                    # Create context for nested AST
                    child_context = ProcessingContext(ast=node.children, node_index=child_index)
                    rendered = self.handlers.process_ast_node(child_context)
                    if rendered:
                        result_parts.append(rendered)

            return "".join(result_parts)

        return [
            ProcessorRule(
                node_type=SectionNode,
                processor_func=process_section_node
            ),
            ProcessorRule(
                node_type=IncludeNode,
                processor_func=process_include_node
            )
        ]

    def register_resolvers(self) -> List[ResolverRule]:
        """
        Registers AST node resolvers for basic placeholders.
        """
        def resolve_section_or_include(node: TemplateNode, context: str) -> TemplateNode:
            """Resolves SectionNode and IncludeNode."""
            if not isinstance(node, (SectionNode, IncludeNode)):
                # Not our node
                return node

            # Use singleton resolver instance (with saved stack)
            if self._resolver is None:
                raise RuntimeError("Resolver not initialized. Call initialize() first.")
            return self._resolver.resolve_node(node, context)

        return [
            ResolverRule(
                node_type=SectionNode,
                resolver_func=resolve_section_or_include
            ),
            ResolverRule(
                node_type=IncludeNode,
                resolver_func=resolve_section_or_include
            )
        ]


__all__ = ["CommonPlaceholdersPlugin"]
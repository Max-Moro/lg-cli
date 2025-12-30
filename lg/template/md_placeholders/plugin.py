"""
Plugin for processing Markdown placeholders.

Registers all necessary tokens, parsing rules, and handlers
for supporting ${md:path}, ${md@origin:path}, globs, anchors and parameters.
"""

from __future__ import annotations

from typing import List

from .nodes import MarkdownFileNode
from .parser_rules import get_md_parser_rules
from .tokens import get_md_token_specs
from .virtual_sections import VirtualSectionFactory
from ..addressing import ResourceKind
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ProcessingContext
from ...template import TemplateContext


class MdPlaceholdersPlugin(TemplatePlugin):
    """
    Plugin for processing Markdown placeholders.

    Provides functionality:
    - ${md:path} - direct Markdown file inclusion
    - ${md:path#anchor} - inclusion of specific section
    - ${md:path,level:3,strip_h1:true} - inclusion with parameters
    - ${md@origin:path} - addressed references to files in other scopes
    - ${md:docs/*} - globs for including multiple files
    - ${md:path,if:tag:condition} - conditional inclusions
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Initializes plugin with template context.

        Args:
            template_ctx: Template context for state management
        """
        super().__init__()
        self.template_ctx = template_ctx

        # Virtual section factory (created once)
        self.virtual_factory = VirtualSectionFactory()

    @property
    def name(self) -> str:
        """Returns plugin name."""
        return "md_placeholders"

    @property
    def priority(self) -> PluginPriority:
        """Returns plugin priority."""
        return PluginPriority.PLACEHOLDER

    def initialize(self) -> None:
        """Adds MD-specific tokens to placeholder context."""
        # Add tokens to existing placeholder context
        # Don't add MD_PREFIX since 'md' is checked via IDENTIFIER
        self.registry.register_tokens_in_context(
            "placeholder",
            ["HASH", "COMMA", "BOOL_TRUE", "BOOL_FALSE", "NUMBER", "GLOB_STAR"]
        )

    def register_tokens(self) -> List[TokenSpec]:
        """Registers tokens for MD placeholders."""
        return get_md_token_specs()

    def register_parser_rules(self) -> List[ParsingRule]:
        """Registers parsing rules for MD placeholders."""
        return get_md_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Registers AST node handlers.

        Creates closures over typed handlers for processing MD nodes.
        """
        def process_markdown_node(processing_context: ProcessingContext) -> str:
            """Processes MarkdownFileNode through virtual section."""
            node = processing_context.get_node()
            if not isinstance(node, MarkdownFileNode):
                raise RuntimeError(f"Expected MarkdownFileNode, got {type(node)}")

            # Check inclusion condition if set
            if node.condition:
                should_include = self.template_ctx.evaluate_condition_text(node.condition)
                if not should_include:
                    return ""

            # Use ProcessingContext for analyzing heading context
            from .heading_context import detect_heading_context_for_node
            heading_context = detect_heading_context_for_node(processing_context)

            # Determine resource kind and build raw path for resolution
            if node.origin is not None:
                # md@origin:path - file inside lg-cfg/ of specified scope
                kind = ResourceKind.MARKDOWN
                # Reconstruct @origin:path format for PathParser to recognize explicit origin
                raw_path = f"@{node.origin}:{node.path}"
            else:
                # md:path - file relative to current scope root (outside lg-cfg/)
                kind = ResourceKind.MARKDOWN_EXTERNAL
                raw_path = node.path

            # Resolve path using new addressing API
            try:
                resolved = self.template_ctx.resolve_path(raw_path, kind)
            except Exception as e:
                raise RuntimeError(f"Failed to resolve markdown path '{raw_path}': {e}")

            # Create virtual section with resolved scope info
            section_config, section_ref = self.virtual_factory.create_for_markdown_file(
                node=node,
                scope_dir=resolved.scope_dir,
                scope_rel=resolved.scope_rel,
                heading_context=heading_context
            )

            # Set virtual section in context
            self.template_ctx.set_virtual_section(section_config)

            try:
                result = self.handlers.process_section_ref(section_ref)
                return result
            finally:
                self.template_ctx.clear_virtual_section()

        return [
            ProcessorRule(
                node_type=MarkdownFileNode,
                processor_func=process_markdown_node
            )
        ]


__all__ = ["MdPlaceholdersPlugin"]

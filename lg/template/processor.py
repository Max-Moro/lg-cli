"""
Template processor for template engine.

Public API combining all template engine components
into convenient interface for processing templates with support for conditions,
modes, and includes.

Allows extending functionality through plugins.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, Optional

from .context import TemplateContext
from .frontmatter import strip_frontmatter
from .handlers import TemplateProcessorHandlers
from .lexer import ContextualLexer
from .nodes import TemplateNode, TemplateAST, TextNode
from .parser import ModularParser
from .registry import TemplateRegistry
from .types import ProcessingContext
from ..addressing.types import ResolvedSection
from ..run_context import RunContext

logger = logging.getLogger(__name__)


class TemplateProcessingError(Exception):
    """General template processing error."""

    def __init__(self, message: str, template_name: str = "", cause: Optional[Exception] = None):
        super().__init__(f"Template processing error in '{template_name}': {message}")
        self.template_name = template_name
        self.cause = cause


class TemplateProcessor:
    """
    Main template processor.
    """

    def __init__(self, run_ctx: RunContext, registry: TemplateRegistry):
        """
        Initializes template processor.

        Args:
            run_ctx: Execution context with settings and services
            registry: Component registry (passed externally to avoid global state)
        """
        self.run_ctx = run_ctx
        self.template_ctx = TemplateContext(run_ctx)

        # Use passed registry or create new one
        self.registry = registry

        # Initialize components
        self.lexer = ContextualLexer(self.registry)
        self.parser = ModularParser(self.registry)

        # Caches for performance
        self._template_cache: Dict[str, TemplateAST] = {}

        # Section handler (set externally)
        self.section_handler: Optional[Callable[[ResolvedSection, TemplateContext], str]] = None

        # Create handlers class inline here
        class ProcessorHandlers(TemplateProcessorHandlers):
            def process_ast_node(self, context: ProcessingContext) -> str:
                """Delegates node processing with context."""
                return processor_self._evaluate_node(context.get_node(), context.ast, context.node_index)

            def process_section(self, resolved: ResolvedSection) -> str:
                """Process resolved section."""
                if processor_self.section_handler is None:
                    raise RuntimeError(f"No section handler set for processing section '{resolved.name}'")
                return processor_self.section_handler(resolved, processor_self.template_ctx)

            def parse_next_node(self, context) -> Optional[TemplateNode]:
                """Delegates parsing to main parser."""
                # noinspection PyProtectedMember
                return processor_self.parser._parse_next_node(context)

            def resolve_ast(self, ast, context: str = "") -> list:
                """Delegates resolving to processor."""
                return processor_self._resolve_template_references(ast, context)

        # Save self reference for closure
        processor_self = self
        self.handlers = ProcessorHandlers()

    def set_section_handler(self, handler: Callable[[ResolvedSection, TemplateContext], str]) -> None:
        """
        Sets section handler.

        Args:
            handler: Function for processing resolved sections
        """
        self.section_handler = handler

    def process_template_file(self, template_name: str) -> str:
        """
        Processes template from file lg-cfg/<name>.tpl.md or lg-cfg/<name>.ctx.md.

        Args:
            template_name: Template name (without .tpl.md/.ctx.md suffix)

        Returns:
            Rendered template text

        Raises:
            TemplateProcessingError: If template processing error occurs
        """
        def process_file():
            template_path, template_text = self._load_template_with_path(template_name)

            # Strip frontmatter from context files (used internally for include directive)
            # Frontmatter should never appear in rendered output
            template_text = strip_frontmatter(template_text)

            # Initialize AddressingContext with current template's directory
            # This enables relative path resolution from the template's location
            with self.run_ctx.addressing.file_scope(template_path):
                rendered = self.process_template_text(template_text, template_name)

            return rendered

        return self._handle_template_errors(
            process_file,
            template_name,
            "Failed to process template file"
        )

    def process_template_text(self, template_text: str, template_name: str = "") -> str:
        """
        Processes template from text.

        Args:
            template_text: Template text to process
            template_name: Optional template name for diagnostics

        Returns:
            Rendered text

        Raises:
            TemplateProcessingError: If template processing error occurs
        """
        def process_text():
            # 1. Parse template into AST
            ast = self._parse_template(template_text, template_name)

            # 2. Resolve references in AST
            resolved_ast = self._resolve_template_references(ast, template_name)

            # 3. Process resolved AST
            return self._evaluate_ast(resolved_ast)

        return self._handle_template_errors(
            process_text,
            template_name,
            "Unexpected error during processing"
        )

    # ======= Internal methods =======

    def _parse_template(self, template_text: str, template_name: str) -> TemplateAST:
        """Parses template text into AST with caching."""
        cache_key = f"{template_name}:{hash(template_text)}"
        
        if cache_key not in self._template_cache:
            try:
                tokens = self.lexer.tokenize(template_text)
                ast = self.parser.parse(tokens)
                self._template_cache[cache_key] = ast
            except Exception as e:
                raise TemplateProcessingError(f"Failed to parse template: {e}", template_name, e)
        
        return self._template_cache[cache_key]

    def _evaluate_ast(self, ast: TemplateAST) -> str:
        """Evaluates AST and returns rendered text."""
        try:
            result_parts = []

            for i, node in enumerate(ast):
                rendered = self._evaluate_node(node, ast, i)
                if rendered:
                    result_parts.append(rendered)

            return "".join(result_parts)
        except Exception as e:
            raise TemplateProcessingError(f"Failed to evaluate AST: {e}", cause=e)

    def _evaluate_node(self, node: TemplateNode, ast: TemplateAST, node_index: int) -> str:
        """Evaluates single AST node."""
        from .types import ProcessingContext

        # Create processing context
        processing_context = ProcessingContext(ast=ast, node_index=node_index)

        # Get processors for this node type
        processors = self.registry.get_processors_for_node(type(node))

        if processors:
            # Use first (highest priority) processor
            processor_rule = processors[0]
            return processor_rule.processor_func(processing_context)

        # Fallback for base nodes
        if isinstance(node, TextNode):
            return node.text

        # Unknown node type - return stub
        logger.warning(f"No processor found for node type: {type(node).__name__}")
        return f"[{type(node).__name__}]"

    def _load_template_with_path(self, template_name: str) -> tuple[Path, str]:
        """
        Loads template text and returns both path and content.

        Used by process_template_file() to initialize AddressingContext
        with the correct current directory.

        Args:
            template_name: Template name (without suffix)

        Returns:
            Tuple of (template_path, template_text)

        Raises:
            TemplateProcessingError: If template not found
        """
        from .common import load_context_from, load_template_from

        cfg_root = self.run_ctx.root / "lg-cfg"

        try:
            # Try to load as context
            path, text = load_context_from(cfg_root, template_name)
            return path, text
        except (FileNotFoundError, RuntimeError):
            try:
                # Try to load as template
                path, text = load_template_from(cfg_root, template_name)
                return path, text
            except (FileNotFoundError, RuntimeError):
                raise TemplateProcessingError(f"Template not found: {template_name}")

    def _load_template_text(self, template_name: str) -> str:
        """Loads template text from file."""
        _, text = self._load_template_with_path(template_name)
        return text

    def _resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Recursively resolves all references in AST through plugins.

        Args:
            ast: AST to resolve
            template_name: Template name for diagnostics

        Returns:
            AST with resolved references
        """
        try:
            resolved_nodes = []
            for node in ast:
                resolved_node = self._resolve_node(node, template_name)
                resolved_nodes.append(resolved_node)
            return resolved_nodes
        except Exception as e:
            raise TemplateProcessingError(f"Failed to resolve template references: {e}", template_name, e)

    def _resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """
        Recursively resolves single AST node.

        Uses plugin resolvers for specific node types,
        automatically processes nested structures via reflection.
        """
        from dataclasses import fields, replace

        # Try to apply plugin-specific resolvers
        resolved = self._apply_plugin_resolvers(node, context)
        if resolved is not node:
            # Plugin processed node - return as-is WITHOUT recursive processing
            # Important: plugin resolver already processed nested nodes
            return resolved

        has_changes = False
        updates = {}

        for field in fields(node):
            field_value = getattr(node, field.name)

            # Handle lists of nodes
            if isinstance(field_value, list):
                if field_value and all(isinstance(item, TemplateNode) for item in field_value):
                    resolved_list = [self._resolve_node(n, context) for n in field_value]
                    updates[field.name] = resolved_list
                    has_changes = True

            # Handle single nodes
            elif isinstance(field_value, TemplateNode):
                resolved = self._resolve_node(field_value, context)
                if resolved is not field_value:
                    updates[field.name] = resolved
                    has_changes = True

        if has_changes:
            return replace(node, **updates)

        return node

    def _apply_plugin_resolvers(self, node: TemplateNode, context: str) -> TemplateNode:
        """
        Applies plugin resolvers to node via registry.

        Uses registered resolvers for specific node types.
        """
        # Get resolvers for node type
        resolvers = self.registry.get_resolvers_for_node(type(node))

        if not resolvers:
            # No registered resolvers for this type
            return node

        # Apply resolver with highest priority
        resolver_rule = resolvers[0]
        return resolver_rule.resolver_func(node, context)

    def _handle_template_errors(self, func, template_name: str, error_message: str):
        """General error handler for template operations."""
        try:
            return func()
        except TemplateProcessingError:
            # Pass processing errors as-is
            raise
        except Exception as e:
            # Wrap other errors in TemplateProcessingError
            raise TemplateProcessingError(error_message, template_name, e)


def create_template_processor(run_ctx: RunContext) -> TemplateProcessor:
    """
    Creates template processor with available plugins already set up.

    Args:
        run_ctx: Execution context

    Returns:
        Configured template processor
    """
    # Create new registry for this processor
    registry = TemplateRegistry()

    # Create processor (handlers auto-configure in constructor)
    processor = TemplateProcessor(run_ctx, registry)

    # Register available plugins (in priority order)
    from .common_placeholders.plugin import CommonPlaceholdersPlugin
    from .adaptive.plugin import AdaptivePlugin
    from .md_placeholders.plugin import MdPlaceholdersPlugin
    from .task_placeholder.plugin import TaskPlaceholderPlugin

    registry.register_plugin(CommonPlaceholdersPlugin(processor.template_ctx))
    registry.register_plugin(AdaptivePlugin(processor.template_ctx))
    registry.register_plugin(MdPlaceholdersPlugin(processor.template_ctx))
    registry.register_plugin(TaskPlaceholderPlugin(processor.template_ctx))

    # Initialize plugins after all components registered
    registry.initialize_plugins(processor.handlers)

    return processor


__all__ = ["TemplateProcessor", "TemplateProcessingError", "create_template_processor"]
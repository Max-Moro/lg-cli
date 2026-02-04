"""
Section collector for template analysis.

Collects all sections referenced in a context template
without performing full rendering. Used for building
the complete adaptive model for a context.

This module belongs in the template package because it:
- Traverses template AST structures
- Uses template-specific node types
- Creates template registry for parsing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Optional, cast

from ...adaptive.errors import AdaptiveError
from ...addressing import AddressingContext, SECTION_CONFIG
from ...addressing.errors import ScopeNotFoundError as AddressScopeNotFoundError
from ...addressing.types import ResolvedSection
from ...section import SectionService
from ...section.service import SectionNotFoundError
from ..common import load_context_from, load_template_from
from ..common_placeholders.nodes import SectionNode, IncludeNode
from ..adaptive.nodes import ConditionalBlockNode, ModeBlockNode
from ..frontmatter import parse_frontmatter, ContextFrontmatter
from ..nodes import TemplateNode, TemplateAST
from ..parser import parse_template
from ..registry import TemplateRegistry


@dataclass
class CollectedSections:
    """
    Result of collecting sections from a context.

    Separates template sections (renderable) from frontmatter sections (meta).
    Both are deduplicated by canonical key.
    """
    template_sections: List[ResolvedSection] = field(default_factory=list)
    frontmatter_sections: List[ResolvedSection] = field(default_factory=list)
    _seen_keys: Set[str] = field(default_factory=set)

    def add_template_section(self, resolved: ResolvedSection) -> bool:
        """
        Add section from template if not already present.

        Args:
            resolved: Resolved section to add

        Returns:
            True if added, False if already present
        """
        canon_key = resolved.canon_key()
        if canon_key in self._seen_keys:
            return False
        self._seen_keys.add(canon_key)
        self.template_sections.append(resolved)
        return True

    def add_frontmatter_section(self, resolved: ResolvedSection) -> bool:
        """
        Add section from frontmatter include if not already present.

        Args:
            resolved: Resolved section to add

        Returns:
            True if added, False if already present
        """
        canon_key = resolved.canon_key()
        if canon_key in self._seen_keys:
            return False
        self._seen_keys.add(canon_key)
        self.frontmatter_sections.append(resolved)
        return True

    def all_sections(self) -> List[ResolvedSection]:
        """
        Get all sections (template + frontmatter) in order.

        Used for building adaptive model where all sections contribute.
        """
        return self.template_sections + self.frontmatter_sections


class SectionCollector:
    """
    Collector for sections referenced in a context template.

    Traverses the template AST to find all section references,
    including those in conditional blocks (without evaluating conditions).
    Also processes frontmatter `include` directives.

    Excludes ${md:...} placeholders as they don't contribute adaptive data.
    """

    def __init__(
        self,
        section_service: SectionService,
        addressing: AddressingContext,
        cfg_root: Path,
    ):
        """
        Initialize collector.

        Args:
            section_service: Service for resolving sections
            addressing: Addressing context for path resolution
            cfg_root: Root lg-cfg directory
        """
        self._section_service = section_service
        self._addressing = addressing
        self._cfg_root = cfg_root
        self._registry: Optional[TemplateRegistry] = None
        self._visited_includes: Set[str] = set()

    def collect(self, context_name: str) -> CollectedSections:
        """
        Collect all sections from a context.

        Traverses the context template and all includes (tpl, ctx)
        to find section references. Processes frontmatter for
        additional include directives.

        Args:
            context_name: Name of the context (without .ctx.md suffix)

        Returns:
            CollectedSections with all found sections
        """
        result = CollectedSections()
        self._visited_includes.clear()

        # Load context file
        template_path, template_text = load_context_from(self._cfg_root, context_name)

        # Parse frontmatter
        frontmatter, content_text = parse_frontmatter(template_text)

        # Parse template AST
        ast = self._parse_template(content_text)

        # Set up addressing context for this file
        with self._addressing.file_scope(template_path):
            # Collect from AST
            self._collect_from_ast(ast, result)

            # Process frontmatter includes
            self._process_frontmatter_includes(frontmatter, result)

        return result

    def _get_registry(self) -> TemplateRegistry:
        """Get or create template registry for parsing."""
        if self._registry is None:
            self._registry = self._create_minimal_registry()
        return self._registry

    def _create_minimal_registry(self) -> TemplateRegistry:
        """
        Create a minimal template registry for parsing.

        Only registers tokens and rules needed for AST structure,
        not full processing capabilities.

        Note: MdPlaceholdersPlugin is NOT registered because:
        1. ${md:...} nodes don't contribute mode-sets/tag-sets
        2. They are explicitly skipped in _collect_from_node()
        3. Without the plugin, ${md:...} becomes TextNode (harmless for collection)
        """
        # Import plugins locally to avoid circular imports at module level
        from ..common_placeholders.plugin import CommonPlaceholdersPlugin
        from ..adaptive.plugin import AdaptivePlugin
        from ..parser import ModularParser
        from ..handlers import TemplateProcessorHandlers
        from ..types import ProcessingContext

        # Create registry
        registry = TemplateRegistry()

        # Create parser (needed for handlers)
        parser = ModularParser(registry)

        # Create minimal handlers that delegate to parser
        # noinspection PyProtectedMember
        class MinimalHandlers(TemplateProcessorHandlers):
            def parse_next_node(self, context) -> Optional[TemplateNode]:
                return parser._parse_next_node(context)

            def process_ast_node(self, context: ProcessingContext) -> str:
                return ""  # Not used for collection

            def process_section(self, resolved) -> str:
                return ""  # Not used for collection

            def resolve_ast(self, ast, context: str = "") -> list:
                return ast  # Not used for collection

        handlers = MinimalHandlers()

        # Create minimal template context mock
        # Only what plugins need for initialization
        class _DummyAddressing:
            def resolve(self, _name, _config):
                return None

        class _DummyRunContext:
            def __init__(self):
                self.addressing = _DummyAddressing()

        class _DummyTemplateContext:
            def __init__(self):
                self.run_ctx = _DummyRunContext()

            def evaluate_condition(self, _condition_ast) -> bool:
                return False

            def evaluate_condition_text(self, _text: str) -> bool:
                return False

            def enter_mode_block(self, modeset: str, mode: str) -> None:
                pass

            def exit_mode_block(self) -> None:
                pass

            def get_effective_task_text(self):
                return None

        dummy_ctx = _DummyTemplateContext()

        # Register plugins with proper template context
        # Note: NOT registering MdPlaceholdersPlugin (see docstring)
        registry.register_plugin(CommonPlaceholdersPlugin(dummy_ctx))
        registry.register_plugin(AdaptivePlugin(dummy_ctx))

        # Initialize plugins with handlers (critical for {% if %} blocks)
        registry.initialize_plugins(handlers)

        return registry

    def _parse_template(self, text: str) -> TemplateAST:
        """Parse template text into AST."""
        return parse_template(text, self._get_registry())

    def _collect_from_ast(self, ast: TemplateAST, result: CollectedSections) -> None:
        """
        Recursively collect sections from AST nodes.

        Traverses all branches of conditional blocks without evaluating.
        """
        for node in ast:
            self._collect_from_node(node, result)

    def _collect_from_node(self, node: TemplateNode, result: CollectedSections) -> None:
        """Process single AST node for section collection."""

        if isinstance(node, SectionNode):
            # Direct section reference
            self._collect_section(node.name, result)

        elif isinstance(node, IncludeNode):
            # Template/context include - traverse recursively
            self._collect_from_include(node, result)

        elif isinstance(node, ConditionalBlockNode):
            # Collect from ALL branches (don't evaluate condition)
            self._collect_from_ast(node.body, result)
            for elif_block in node.elif_blocks:
                self._collect_from_ast(elif_block.body, result)
            if node.else_block:
                self._collect_from_ast(node.else_block.body, result)

        elif isinstance(node, ModeBlockNode):
            # Collect from mode block body
            self._collect_from_ast(node.body, result)

        # Note: ${md:...} nodes are intentionally skipped
        # They don't contribute mode-sets/tag-sets

    def _collect_section(self, section_name: str, result: CollectedSections) -> None:
        """
        Resolve and add template section to result.

        Args:
            section_name: Section name from template
            result: CollectedSections to add to
        """
        try:
            resolved = cast(
                ResolvedSection,
                self._addressing.resolve(section_name, SECTION_CONFIG)
            )
            result.add_template_section(resolved)
        except (SectionNotFoundError, AdaptiveError, AddressScopeNotFoundError):
            # Section not found or adaptive config error - skip during collection.
            # Errors will surface during actual rendering.
            pass

    def _collect_from_include(self, node: IncludeNode, result: CollectedSections) -> None:
        """
        Process include node and collect sections from included template.

        Handles circular include detection.
        """
        # Build include key for cycle detection
        include_key = node.canon_key()

        if include_key in self._visited_includes:
            # Already visited - skip to avoid infinite loop
            return

        self._visited_includes.add(include_key)

        try:
            # Determine which loader to use
            if node.kind == "ctx":
                loader = load_context_from
            else:
                loader = load_template_from

            # Resolve the include path
            if node.origin and node.origin != "self":
                # Addressed include - need to resolve scope
                scope_dir = (self._addressing.cfg_root.parent / node.origin).resolve()
                cfg_root = scope_dir / "lg-cfg"
            else:
                cfg_root = self._cfg_root

            # Load and parse
            template_path, template_text = loader(cfg_root, node.name)

            # For contexts, strip frontmatter
            if node.kind == "ctx":
                _, template_text = parse_frontmatter(template_text)

            ast = self._parse_template(template_text)

            # Collect with proper file scope
            with self._addressing.file_scope(template_path, node.origin if node.origin != "self" else None):
                self._collect_from_ast(ast, result)

        except (RuntimeError, FileNotFoundError, AdaptiveError, AddressScopeNotFoundError):
            # Include not found or config error - skip during collection
            pass

    def _process_frontmatter_includes(
        self,
        frontmatter: Optional[ContextFrontmatter],
        result: CollectedSections
    ) -> None:
        """
        Process sections from frontmatter include directive.

        These are typically meta-sections for adaptive configuration.
        They are stored separately and don't appear in renderable sections list.
        """
        if not frontmatter or not frontmatter.include:
            return

        for section_ref in frontmatter.include:
            try:
                resolved = cast(
                    ResolvedSection,
                    self._addressing.resolve(section_ref, SECTION_CONFIG)
                )
                result.add_frontmatter_section(resolved)
            except (SectionNotFoundError, AdaptiveError, AddressScopeNotFoundError):
                # Section not found - skip during collection
                pass


__all__ = ["SectionCollector", "CollectedSections"]

"""
Reference resolver for basic section and template placeholders.

Handles addressed references and loading of included templates from other lg-cfg scopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, cast

from .nodes import SectionNode, IncludeNode
from ..common import load_template_from, load_context_from
from ..handlers import TemplateProcessorHandlers
from ..nodes import TemplateNode, TemplateAST
from ..protocols import TemplateRegistryProtocol
from ..addressing import ResourceKind
from ...types import SectionRef


@dataclass(frozen=True)
class ResolvedInclude:
    """Result of resolving an inclusion with loaded and parsed AST."""
    kind: str  # "tpl" | "ctx"
    name: str
    origin: str
    cfg_root: Path
    ast: TemplateAST


class CommonPlaceholdersResolver:
    """
    Reference resolver for basic placeholders.

    Handles addressed references, loads included templates,
    and fills node metadata for subsequent processing.

    Uses AddressingContext from TemplateContext for path resolution.
    """

    def __init__(
            self,
            handlers: TemplateProcessorHandlers,
            registry: TemplateRegistryProtocol,
    ):
        """
        Initializes resolver.

        Args:
            handlers: Typed handlers for template parsing
            registry: Registry of components for parsing
        """
        self.handlers: TemplateProcessorHandlers = handlers
        self.registry = registry

        # Cache of resolved inclusions
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []

        # Reference to template_ctx will be obtained through handlers
        self._template_ctx = None

    def _get_template_ctx(self):
        """Lazily get template context from processor."""
        if self._template_ctx is None:
            raise RuntimeError("Template context not set. Call set_template_ctx() first.")
        return self._template_ctx

    def set_template_ctx(self, template_ctx) -> None:
        """Set template context for path resolution."""
        self._template_ctx = template_ctx

    def resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """
        Resolves a basic placeholder node (SectionNode or IncludeNode).

        Public method for use by processor.
        """
        if isinstance(node, SectionNode):
            return self._resolve_section_node(node, context)
        elif isinstance(node, IncludeNode):
            return self._resolve_include_node(node, context)
        else:
            return node

    def _resolve_section_node(self, node: SectionNode, _context: str = "") -> SectionNode:
        """
        Resolves section node using new addressing API.
        """
        section_name = node.section_name
        template_ctx = self._get_template_ctx()

        try:
            # Use new addressing API
            resolved = template_ctx.resolve_path(section_name, ResourceKind.SECTION)

            # Create SectionRef from resolved path
            section_ref = SectionRef(
                name=resolved.canonical_id or resolved.resource_rel,
                scope_rel=resolved.scope_rel,
                scope_dir=resolved.scope_dir
            )

            return SectionNode(
                section_name=resolved.canonical_id or resolved.resource_rel,
                resolved_ref=section_ref
            )

        except Exception as e:
            raise RuntimeError(f"Failed to resolve section '{section_name}': {e}")

    def _resolve_include_node(self, node: IncludeNode, context: str = "") -> IncludeNode:
        """
        Resolves include node, loads and parses the included template.
        """
        cache_key = node.canon_key()

        # Check for circular dependencies
        if cache_key in self._resolution_stack:
            cycle_info = " -> ".join(self._resolution_stack + [cache_key])
            raise RuntimeError(f"Circular include dependency: {cycle_info}")

        # Check cache
        if cache_key in self._resolved_includes:
            resolved_include = self._resolved_includes[cache_key]
            return IncludeNode(
                kind=node.kind,
                name=node.name,
                origin=resolved_include.origin,
                children=resolved_include.ast
            )

        # Resolve the include
        self._resolution_stack.append(cache_key)
        try:
            resolved_include = self._load_and_parse_include(node, context)
            self._resolved_includes[cache_key] = resolved_include

            return IncludeNode(
                kind=node.kind,
                name=node.name,
                origin=resolved_include.origin,
                children=resolved_include.ast
            )
        finally:
            self._resolution_stack.pop()

    def _load_and_parse_include(self, node: IncludeNode, context: str) -> ResolvedInclude:
        """
        Loads and parses the included template using new addressing API.
        """
        template_ctx = self._get_template_ctx()

        # Determine resource kind
        kind = ResourceKind.CONTEXT if node.kind == "ctx" else ResourceKind.TEMPLATE

        # Build raw path for resolution
        if node.origin and node.origin != "self":
            raw_path = f"@{node.origin}:{node.name}"
        else:
            raw_path = node.name

        # Resolve path using new API
        resolved = template_ctx.resolve_path(raw_path, kind)

        # Load content from resolved path
        if node.kind == "ctx":
            _, template_text = load_context_from(resolved.cfg_root, resolved.resource_rel.replace('.ctx.md', ''))
        else:
            _, template_text = load_template_from(resolved.cfg_root, resolved.resource_rel.replace('.tpl.md', ''))

        # Parse template
        from ..parser import parse_template
        from ..registry import TemplateRegistry
        include_ast = parse_template(template_text, registry=cast(TemplateRegistry, self.registry))

        # Apply resolvers with file scope context
        with template_ctx.file_scope(resolved.resource_path, resolved.scope_rel):
            # Core will apply resolvers from all plugins
            ast: TemplateAST = self.handlers.resolve_ast(include_ast, context)

        # Determine effective origin
        effective_origin = resolved.scope_rel if resolved.scope_rel else "self"

        return ResolvedInclude(
            kind=node.kind,
            name=node.name,
            origin=effective_origin,
            cfg_root=resolved.cfg_root,
            ast=ast
        )


__all__ = ["CommonPlaceholdersResolver", "ResolvedInclude"]
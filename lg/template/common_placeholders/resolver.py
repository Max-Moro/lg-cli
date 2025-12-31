"""
Reference resolver for basic section and template placeholders.

Handles addressed references and loading of included templates from other lg-cfg scopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, cast

from .configs import TEMPLATE_CONFIG, CONTEXT_CONFIG, SECTION_CONFIG
from .nodes import SectionNode, IncludeNode
from ..common import load_template_from, load_context_from
from ..handlers import TemplateProcessorHandlers
from ..nodes import TemplateNode, TemplateAST
from ..protocols import TemplateRegistryProtocol
from ...addressing import AddressingContext
from ...addressing.types import ResolvedSection, ResolvedFile


@dataclass(frozen=True)
class ResolvedInclude:
    """Result of resolving an inclusion with loaded and parsed AST."""
    kind: str  # "tpl" | "ctx"
    name: str
    origin: str
    cfg_root: Path
    resource_path: Path  # Full path to the included file
    ast: TemplateAST


class CommonPlaceholdersResolver:
    """
    Reference resolver for basic placeholders.

    Handles addressed references, loads included templates,
    and fills node metadata for subsequent processing.

    Uses unified AddressingContext.resolve() for all resource types.
    """

    def __init__(
            self,
            handlers: TemplateProcessorHandlers,
            registry: TemplateRegistryProtocol,
            addressing: AddressingContext,
    ):
        """
        Initializes resolver.

        Args:
            handlers: Typed handlers for template parsing
            registry: Registry of components for parsing
            addressing: Addressing context for path resolution
        """
        self.handlers: TemplateProcessorHandlers = handlers
        self.registry: TemplateRegistryProtocol = registry
        self.addressing: AddressingContext = addressing

        # Cache of resolved inclusions
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []

    def resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """
        Resolves a basic placeholder node (SectionNode or IncludeNode).

        Public method for use by processor.
        """
        if isinstance(node, SectionNode):
            return self._resolve_section_node(node)
        elif isinstance(node, IncludeNode):
            return self._resolve_include_node(node, context)
        else:
            return node

    def _resolve_section_node(self, node: SectionNode) -> SectionNode:
        """
        Resolves section node using unified addressing API.
        """
        # Use unified resolve() with SECTION_CONFIG
        resolved = self.addressing.resolve(node.name, SECTION_CONFIG)

        # Type narrowing - we know it's ResolvedSection because is_section=True
        resolved_section = cast(ResolvedSection, resolved)

        return SectionNode(node.name, resolved_section=resolved_section)

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
                children=resolved_include.ast,
                resolved_path=resolved_include.resource_path
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
                children=resolved_include.ast,
                resolved_path=resolved_include.resource_path
            )
        finally:
            self._resolution_stack.pop()

    def _load_and_parse_include(self, node: IncludeNode, context: str) -> ResolvedInclude:
        """
        Loads and parses the included template using unified addressing API.
        """
        # Determine resource config
        config = CONTEXT_CONFIG if node.kind == "ctx" else TEMPLATE_CONFIG

        # Build raw path for resolution
        if node.origin and node.origin != "self":
            raw_path = f"@{node.origin}:{node.name}"
        else:
            raw_path = node.name

        # Use unified resolve()
        resolved_file = cast(ResolvedFile, self.addressing.resolve(raw_path, config))

        # Load content from resolved path
        if node.kind == "ctx":
            _, template_text = load_context_from(resolved_file.cfg_root, resolved_file.resource_rel.replace('.ctx.md', ''))
        else:
            _, template_text = load_template_from(resolved_file.cfg_root, resolved_file.resource_rel.replace('.tpl.md', ''))

        # Parse template
        from ..parser import parse_template
        from ..registry import TemplateRegistry
        include_ast = parse_template(template_text, registry=cast(TemplateRegistry, self.registry))

        # Apply resolvers with file scope context
        with self.addressing.file_scope(resolved_file.resource_path, resolved_file.scope_rel):
            # Core will apply resolvers from all plugins
            ast: TemplateAST = self.handlers.resolve_ast(include_ast, context)

        # Determine effective origin
        effective_origin = resolved_file.scope_rel if resolved_file.scope_rel else "self"

        return ResolvedInclude(
            kind=node.kind,
            name=node.name,
            origin=effective_origin,
            cfg_root=resolved_file.cfg_root,
            resource_path=resolved_file.resource_path,
            ast=ast
        )


__all__ = ["CommonPlaceholdersResolver", "ResolvedInclude"]
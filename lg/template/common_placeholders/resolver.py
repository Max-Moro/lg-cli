"""
Reference resolver for basic section and template placeholders.

Handles addressed references and loading of included templates from other lg-cfg scopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, cast

from .nodes import SectionNode, IncludeNode
from ..common import (
    resolve_cfg_root,
    load_template_from, load_context_from,
    merge_origins
)
from ..handlers import TemplateProcessorHandlers
from ..nodes import TemplateNode, TemplateAST
from ..protocols import TemplateRegistryProtocol
from ...run_context import RunContext
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
    """

    def __init__(
            self,
            run_ctx: RunContext,
            handlers: TemplateProcessorHandlers,
            registry: TemplateRegistryProtocol,
    ):
        """
        Initializes resolver.

        Args:
            run_ctx: Runtime context with settings and paths
            handlers: Typed handlers for template parsing
            registry: Registry of components for parsing
        """
        self.run_ctx = run_ctx
        self.handlers: TemplateProcessorHandlers = handlers
        self.registry = registry
        self.repo_root = run_ctx.root
        self.current_cfg_root = run_ctx.root / "lg-cfg"

        # Stack of origins for supporting nested inclusions
        self._origin_stack: List[str] = ["self"]

        # Cache of resolved inclusions
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []

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
            # Not our node - return as is
            return node

    def _resolve_section_node(self, node: SectionNode, _context: str = "") -> SectionNode:
        """
        Resolves section node, handling addressed references.

        Supports formats:
        - "section_name" → current scope (uses origin stack)
        - "@origin:section_name" → specified scope
        - "@[origin]:section_name" → scope with colons in name
        """
        section_name = node.section_name
        
        try:
            # Always use _parse_section_reference
            cfg_root, resolved_name = self._parse_section_reference(section_name)

            # Create SectionRef for use in the rest of the pipeline
            scope_dir = cfg_root.parent.resolve()
            try:
                scope_rel = scope_dir.relative_to(self.repo_root.resolve()).as_posix()
                if scope_rel == ".":
                    scope_rel = ""
            except ValueError:
                raise RuntimeError(f"Scope directory outside repository: {scope_dir}")
            
            section_ref = SectionRef(
                name=resolved_name,
                scope_rel=scope_rel, 
                scope_dir=scope_dir
            )
            
            return SectionNode(section_name=resolved_name, resolved_ref=section_ref)
            
        except Exception as e:
            raise RuntimeError(f"Failed to resolve section '{section_name}': {e}")

    def _resolve_include_node(self, node: IncludeNode, context: str = "") -> IncludeNode:
        """
        Resolves include node, loads and parses the included template.
        """
        # Create cache key
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
                origin=resolved_include.origin,  # Use effective origin from cache
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
                origin=resolved_include.origin,  # Use effective origin from resolution
                children=resolved_include.ast
            )
        finally:
            self._resolution_stack.pop()

    def _parse_section_reference(self, section_name: str) -> tuple[Path, str]:
        """
        Parses section reference in various formats.

        Args:
            section_name: Section name (may be addressed)

        Returns:
            Tuple (cfg_root, resolved_name)
        """
        if section_name.startswith("@["):
            # Bracket form: @[origin]:name
            close_bracket = section_name.find("]:")
            if close_bracket < 0:
                raise RuntimeError(f"Invalid section reference format: {section_name}")
            origin = section_name[2:close_bracket]
            name = section_name[close_bracket + 2:]
        elif section_name.startswith("@"):
            # Simple addressed form: @origin:name
            colon_pos = section_name.find(":", 1)
            if colon_pos < 0:
                raise RuntimeError(f"Invalid section reference format: {section_name}")
            origin = section_name[1:colon_pos]
            name = section_name[colon_pos + 1:]
        else:
            # Simple reference without addressing - uses current origin from stack
            current_origin = self._origin_stack[-1] if self._origin_stack else "self"
            cfg_root = resolve_cfg_root(
                current_origin,
                current_cfg_root=self.current_cfg_root,
                repo_root=self.repo_root
            )
            return cfg_root, section_name

        # Resolve cfg_root for specified origin
        cfg_root = resolve_cfg_root(
            origin,
            current_cfg_root=self.current_cfg_root,
            repo_root=self.repo_root
        )
        return cfg_root, name

    def _load_and_parse_include(self, node: IncludeNode, context: str) -> ResolvedInclude:
        """
        Loads and parses the included template.

        Args:
            node: Include node to process
            context: Context for diagnostics

        Returns:
            Resolved inclusion with AST
        """
        # Merge base origin from stack with node origin
        base_origin = self._origin_stack[-1] if self._origin_stack else "self"
        effective_origin = merge_origins(base_origin, node.origin)

        # Resolve cfg_root
        cfg_root = resolve_cfg_root(
            effective_origin,
            current_cfg_root=self.current_cfg_root,
            repo_root=self.repo_root
        )

        # Load content
        if node.kind == "ctx":
            _, template_text = load_context_from(cfg_root, node.name)
        elif node.kind == "tpl":
            _, template_text = load_template_from(cfg_root, node.name)
        else:
            raise RuntimeError(f"Unknown include kind: {node.kind}")

        # Parse template
        from ..parser import parse_template
        from ..registry import TemplateRegistry
        include_ast = parse_template(template_text, registry=cast(TemplateRegistry, self.registry))

        # Recursively resolve inclusion with new origin on stack
        self._origin_stack.append(effective_origin)
        try:
            # Core will apply resolvers from all plugins, including ours
            ast: TemplateAST = self.handlers.resolve_ast(include_ast, context)
        finally:
            # Restore origin stack after resolution
            self._origin_stack.pop()

        return ResolvedInclude(
            kind=node.kind,
            name=node.name,
            origin=effective_origin,
            cfg_root=cfg_root,
            ast=ast
        )


__all__ = ["CommonPlaceholdersResolver", "ResolvedInclude"]
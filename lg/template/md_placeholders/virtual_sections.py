"""
Factory for virtual sections for the templating engine.
"""

from __future__ import annotations

from .heading_context import HeadingContext
from .nodes import MarkdownFileNode
from ...addressing.types import ResolvedFile, ResolvedSection
from ...section.model import SectionCfg, AdapterConfig
from ...section import SectionLocation
from ...filtering.model import FilterNode
from ...markdown import MarkdownCfg


class VirtualSectionFactory:
    """
    Factory for creating virtual sections from Markdown files.

    Generates unique sections for processing individual documents
    with automatic adapter configuration based on placeholder parameters.
    """

    def __init__(self):
        """Initializes factory."""
        self._counter = 0

    def create_for_markdown_file(
        self,
        node: MarkdownFileNode,
        resolved: ResolvedFile,
        heading_context: HeadingContext,
    ) -> ResolvedSection:
        """
        Creates virtual section for Markdown file or set of files.

        Args:
            node: MarkdownFileNode with complete information about included file
            resolved: Resolved path from addressing system
            heading_context: Heading context

        Returns:
            resolved_section
        """
        # Use resolved path for md@origin:, otherwise normalize from node for md: (external)
        path = resolved.resource_rel if node.origin is not None else node.path
        prefix = "/lg-cfg" if node.origin is not None else ""
        normalized_path = self._normalize_path_for_filter(path, node.is_glob, prefix)

        # Create filter configuration
        filters = self._create_file_filter(normalized_path)

        # Create Markdown adapter configuration
        markdown_config_raw = self._create_markdown_config(node, heading_context).to_dict()

        # Create full section configuration
        section_config = SectionCfg(
            extensions=[".md"],
            filters=filters,
            adapters={"markdown": AdapterConfig(base_options=markdown_config_raw)}
        )

        # Generate unique name for virtual section
        # Name format: "md:path.md" or "md@origin:path.md" for proper identification
        name = self._generate_name(node)

        # Create synthetic location for virtual section
        synthetic_location = SectionLocation(
            file_path=resolved.resource_path,
            local_name=name
        )

        # Create ResolvedSection with scope info from resolved path
        resolved_section = ResolvedSection(
            scope_dir=resolved.scope_dir,
            scope_rel=resolved.scope_rel,
            location=synthetic_location,
            section_config=section_config,
            name=name
        )

        return resolved_section

    def _generate_name(self, node: MarkdownFileNode) -> str:
        """
        Generates unique name for virtual section.

        Format preserves placeholder syntax for proper identification:
        - "md:path.md" for local files
        - "md@origin:path.md" for addressed files

        Args:
            node: MarkdownFileNode with path and origin info

        Returns:
            String like "md:file.md" or "md@origin:file.md"
        """
        # Build path with .md extension if not present
        path = node.path
        if not path.endswith('.md') and not path.endswith('.markdown'):
            path = f"{path}.md"

        if node.origin is not None:
            return f"md@{node.origin}:{path}"
        return f"md:{path}"

    def _normalize_path_for_filter(self, path: str, is_glob: bool, prefix: str = "") -> str:
        """
        Normalizes path for section filter.

        Args:
            path: File path or glob pattern
            is_glob: True if path contains glob symbols
            prefix: Optional prefix (e.g., "/lg-cfg" for md@origin:)

        Returns:
            Normalized path for allow filter
        """
        normalized = path.strip()

        # Add .md extension only for non-glob paths
        if not is_glob and not normalized.endswith('.md') and not normalized.endswith('.markdown'):
            normalized += '.md'

        # Format with prefix and leading slash
        return f"{prefix}{normalized}" if normalized.startswith('/') else f"{prefix}/{normalized}"

    def _create_file_filter(self, path: str) -> FilterNode:
        """
        Creates filter for including specified files.

        Args:
            path: Normalized file path

        Returns:
            FilterNode with allow mode for specified files
        """
        return FilterNode(mode="allow", allow=[path])

    def _create_markdown_config(
        self,
        node: MarkdownFileNode,
        heading_context: HeadingContext
    ) -> MarkdownCfg:
        """
        Creates Markdown adapter configuration.

        Args:
            node: MarkdownFileNode with complete information about included file
            heading_context: Heading context for parameter determination

        Returns:
            Typed Markdown adapter configuration
        """
        # Get effective values considering priority: explicit > contextual
        effective_heading_level = node.heading_level if node.heading_level is not None else heading_context.heading_level
        effective_strip_h1 = node.strip_h1 if node.strip_h1 is not None else heading_context.strip_h1

        # Create base configuration
        config = MarkdownCfg(
            max_heading_level=effective_heading_level,
            strip_h1=effective_strip_h1 if effective_strip_h1 is not None else False,
            placeholder_inside_heading=heading_context.placeholder_inside_heading
        )

        # If an anchor is present, create keep-configuration to include only the needed section
        if node.anchor:
            from ...markdown.model import MarkdownKeepCfg, SectionRule, SectionMatch
            from ...markdown.slug import slugify_github

            # Create rule for including section by name
            # Use slug-matching for more flexible search
            # Normalize anchor before slug creation (add spaces in reasonable places)
            normalized_anchor = self._normalize_anchor_for_slug(node.anchor)
            anchor_slug = slugify_github(normalized_anchor)
            section_rule = SectionRule(
                match=SectionMatch(
                    kind="slug",
                    pattern=anchor_slug
                ),
                reason=f"md placeholder anchor: #{node.anchor} (slug: {anchor_slug})"
            )
            
            config.keep = MarkdownKeepCfg(
                sections=[section_rule],
                frontmatter=False  # By default, do not include frontmatter for anchor insertions
            )
        
        return config

    def _normalize_anchor_for_slug(self, anchor: str) -> str:
        """
        Normalizes anchor for consistent slug generation.

        Adds spaces after colons and other separators
        so that anchor slug matches real heading slug.

        Args:
            anchor: Original anchor from placeholder

        Returns:
            Normalized anchor
        """
        import re

        # Add space after colon if not present
        # FAQ:Common Questions -> FAQ: Common Questions
        normalized = re.sub(r':(?!\s)', ': ', anchor)

        # Add space after ampersand if not present
        # API&Usage -> API & Usage
        normalized = re.sub(r'&(?!\s)', ' & ', normalized)

        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized


__all__ = ["VirtualSectionFactory"]
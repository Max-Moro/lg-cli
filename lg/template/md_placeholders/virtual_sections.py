"""
Factory for virtual sections for the templating engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .heading_context import HeadingContext
from .nodes import MarkdownFileNode
from ...config.model import SectionCfg, AdapterConfig
from ...filtering.model import FilterNode
from ...markdown import MarkdownCfg
from ...template.common import merge_origins
from ...types import SectionRef


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
        repo_root: Path,
        current_origin: str,
        heading_context: HeadingContext
    ) -> tuple[SectionCfg, SectionRef]:
        """
        Creates virtual section for Markdown file or set of files.

        Args:
            node: MarkdownFileNode with complete information about included file
            repo_root: Repository root for path resolution
            current_origin: Current origin from template context ("self" or scope path)
            heading_context: Heading context

        Returns:
            Tuple (section_config, section_ref)

        Raises:
            ValueError: For invalid parameters
        """
        # Normalize file path(s)
        normalized_path = self._normalize_file_path(node.path, node.origin, node.is_glob)

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

        # Merge base origin from context with node origin
        effective_origin = merge_origins(current_origin, node.origin)

        # Create SectionRef
        if effective_origin == "self":
            # Root scope
            scope_dir = repo_root.resolve()
            scope_rel = ""
        else:
            # Nested or composite scope
            scope_dir = (repo_root / effective_origin).resolve()
            scope_rel = effective_origin

        section_ref = SectionRef(
            name=self._generate_name(),
            scope_rel=scope_rel,
            scope_dir=scope_dir
        )

        return section_config, section_ref

    def _generate_name(self) -> str:
        """
        Generates unique name for virtual section.

        Returns:
            String like "_virtual_<counter>"
        """
        self._counter += 1
        return f"_virtual_{self._counter}"

    def _normalize_file_path(self, path: str, origin: Optional[str], is_glob: bool) -> str:
        """
        Normalizes file path for filter creation.

        Args:
            path: Original file path or glob pattern
            origin: Scope ("self" or scope path, None for regular md:)
            is_glob: True if path contains glob symbols

        Returns:
            Normalized path for allow filter
        """
        # Normalize path
        normalized = path.strip()

        # Automatically add .md extension if missing
        if not is_glob:
            # For regular files, check and add .md
            if not normalized.endswith('.md') and not normalized.endswith('.markdown'):
                normalized += '.md'
        else:
            # For globs, do not add extension automatically
            pass

        # Format different paths based on origin type
        if origin is not None:
            # For @origin: files are ALWAYS searched in lg-cfg/ area of origin scope
            if normalized.startswith('/'):
                return f"/lg-cfg{normalized}"
            else:
                return f"/lg-cfg/{normalized}"

        else:
            # For regular md: files are searched relative to the repository root
            if normalized.startswith('/'):
                return normalized
            else:
                return f"/{normalized}"

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
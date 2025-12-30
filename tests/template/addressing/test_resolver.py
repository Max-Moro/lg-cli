"""
Tests for lg/template/addressing/resolver.py

Tests PathResolver class for resolving paths with file system.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lg.template.addressing import (
    PathParser,
    PathResolver,
    AddressingContext,
    ResourceKind,
    PathResolutionError,
    ScopeNotFoundError,
)


class TestPathResolverBasic:
    """Basic resolution tests for PathResolver."""

    def test_resolve_simple_template(self, addressing_project: Path):
        """Resolve simple template path in root lg-cfg."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("intro", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.kind == ResourceKind.TEMPLATE
        assert resolved.resource_rel == "intro.tpl.md"
        assert resolved.resource_path == addressing_project / "lg-cfg" / "intro.tpl.md"
        assert resolved.scope_rel == ""

    def test_resolve_nested_template(self, addressing_project: Path):
        """Resolve template in subdirectory."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("common/header", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel == "common/header.tpl.md"

    def test_resolve_context(self, addressing_project: Path):
        """Resolve context path adds .ctx.md extension."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("main", ResourceKind.CONTEXT)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel == "main.ctx.md"

    def test_resolve_section(self, addressing_project: Path):
        """Resolve section path does not add extension."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("docs", ResourceKind.SECTION)
        resolved = resolver.resolve(parsed, ctx)

        # For sections, resource_rel serves as canonical ID
        assert resolved.resource_rel == "docs"


class TestPathResolverRelativePaths:
    """Tests for relative path resolution with ../."""

    def test_resolve_parent_reference(self, addressing_project: Path):
        """Resolve path with ../ from nested directory."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        # Simulate being in docs/ directory
        ctx._push_raw("self", "docs", addressing_project / "lg-cfg")

        parsed = parser.parse("../common/header", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel == "common/header.tpl.md"

    def test_resolve_absolute_path_ignores_current_dir(self, addressing_project: Path):
        """Absolute path ignores current directory context."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        # Simulate being in docs/ directory
        ctx._push_raw("self", "docs", addressing_project / "lg-cfg")

        parsed = parser.parse("/common/header", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel == "common/header.tpl.md"
        assert resolved.resource_path == addressing_project / "lg-cfg" / "common" / "header.tpl.md"

    def test_resolve_escaping_boundary_raises_error(self, addressing_project: Path):
        """Path escaping lg-cfg boundary raises error."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("../../outside", ResourceKind.TEMPLATE)

        with pytest.raises(PathResolutionError, match="escapes lg-cfg"):
            resolver.resolve(parsed, ctx)


class TestPathResolverScopes:
    """Tests for scope resolution in multi-scope projects."""

    def test_resolve_in_different_scope(self, multi_scope_project: Path):
        """Resolve path in different scope via @origin:path."""
        resolver = PathResolver(multi_scope_project)
        parser = PathParser()
        ctx = AddressingContext(multi_scope_project, multi_scope_project / "lg-cfg")

        parsed = parser.parse("@apps/web:web", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.scope_rel == "apps/web"
        assert resolved.cfg_root == multi_scope_project / "apps" / "web" / "lg-cfg"
        assert resolved.resource_rel == "web.tpl.md"

    def test_resolve_root_scope_via_slash(self, multi_scope_project: Path):
        """Resolve path in root scope via @/:path."""
        resolver = PathResolver(multi_scope_project)
        parser = PathParser()

        # Start from apps/web scope
        web_cfg = multi_scope_project / "apps" / "web" / "lg-cfg"
        ctx = AddressingContext(multi_scope_project, web_cfg)

        parsed = parser.parse("@/:root", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.scope_rel == ""
        assert resolved.cfg_root == multi_scope_project / "lg-cfg"

    def test_scope_not_found_raises_error(self, multi_scope_project: Path):
        """Non-existent scope raises ScopeNotFoundError."""
        resolver = PathResolver(multi_scope_project)
        parser = PathParser()
        ctx = AddressingContext(multi_scope_project, multi_scope_project / "lg-cfg")

        parsed = parser.parse("@apps/mobile:intro", ResourceKind.TEMPLATE)

        with pytest.raises(ScopeNotFoundError, match="apps/mobile"):
            resolver.resolve(parsed, ctx)


class TestPathResolverExternalMarkdown:
    """Tests for external markdown resolution (relative to repo root)."""

    def test_resolve_external_md_at_repo_root(self, addressing_project: Path):
        """Resolve external markdown at repo root."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse_markdown("README", has_at=False)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.kind == ResourceKind.MARKDOWN_EXTERNAL
        assert resolved.resource_path == addressing_project / "README.md"

    def test_resolve_external_md_in_subdirectory(self, addressing_project: Path):
        """Resolve external markdown in subdirectory."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse_markdown("docs/external", has_at=False)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_path == addressing_project / "docs" / "external.md"

    def test_resolve_internal_md_in_lgcfg(self, addressing_project: Path):
        """Resolve internal markdown (with @) inside lg-cfg."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse_markdown("self:docs/guide", has_at=True)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.kind == ResourceKind.MARKDOWN
        assert resolved.resource_path == addressing_project / "lg-cfg" / "docs" / "guide.md"


class TestPathResolverExtensions:
    """Tests for automatic extension handling."""

    def test_template_extension_added(self, addressing_project: Path):
        """Template paths get .tpl.md extension."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("intro", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel.endswith(".tpl.md")

    def test_context_extension_added(self, addressing_project: Path):
        """Context paths get .ctx.md extension."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("main", ResourceKind.CONTEXT)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel.endswith(".ctx.md")

    def test_explicit_extension_not_duplicated(self, addressing_project: Path):
        """Explicit extension is not duplicated."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse("intro.tpl.md", ResourceKind.TEMPLATE)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel == "intro.tpl.md"
        assert not resolved.resource_rel.endswith(".tpl.md.tpl.md")

    def test_md_extension_added(self, addressing_project: Path):
        """Markdown paths get .md extension."""
        resolver = PathResolver(addressing_project)
        parser = PathParser()
        ctx = AddressingContext(addressing_project, addressing_project / "lg-cfg")

        parsed = parser.parse_markdown("self:docs/guide", has_at=True)
        resolved = resolver.resolve(parsed, ctx)

        assert resolved.resource_rel.endswith(".md")

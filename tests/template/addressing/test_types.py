"""
Tests for lg/template/addressing/types.py

Tests data types: ResourceKind, ParsedPath, ResolvedPath, DirectoryContext.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lg.template.addressing import (
    ResourceKind,
    ParsedPath,
    ResolvedPath,
    DirectoryContext,
)


class TestResourceKind:
    """Tests for ResourceKind enum."""

    def test_has_all_expected_values(self):
        """Verify all resource kinds are defined."""
        assert ResourceKind.SECTION.value == "section"
        assert ResourceKind.TEMPLATE.value == "tpl"
        assert ResourceKind.CONTEXT.value == "ctx"
        assert ResourceKind.MARKDOWN.value == "md"
        assert ResourceKind.MARKDOWN_EXTERNAL.value == "md_external"

    def test_enum_members_count(self):
        """Verify exact number of resource kinds."""
        assert len(ResourceKind) == 5


class TestParsedPath:
    """Tests for ParsedPath dataclass."""

    def test_create_simple_path(self):
        """Create ParsedPath with minimal required fields."""
        parsed = ParsedPath(
            kind=ResourceKind.TEMPLATE,
            origin=None,
            origin_explicit=False,
            path="intro",
            is_absolute=False,
        )

        assert parsed.kind == ResourceKind.TEMPLATE
        assert parsed.origin is None
        assert parsed.origin_explicit is False
        assert parsed.path == "intro"
        assert parsed.is_absolute is False
        assert parsed.anchor is None
        assert parsed.parameters == {}

    def test_create_path_with_origin(self):
        """Create ParsedPath with explicit origin."""
        parsed = ParsedPath(
            kind=ResourceKind.SECTION,
            origin="apps/web",
            origin_explicit=True,
            path="web-src",
            is_absolute=False,
        )

        assert parsed.origin == "apps/web"
        assert parsed.origin_explicit is True

    def test_create_path_with_anchor_and_params(self):
        """Create ParsedPath with anchor and parameters (for md)."""
        parsed = ParsedPath(
            kind=ResourceKind.MARKDOWN,
            origin="self",
            origin_explicit=True,
            path="docs/api",
            is_absolute=False,
            anchor="Authentication",
            parameters={"level": 3, "strip_h1": True},
        )

        assert parsed.anchor == "Authentication"
        assert parsed.parameters == {"level": 3, "strip_h1": True}

    def test_parsed_path_is_frozen(self):
        """Verify ParsedPath is immutable."""
        parsed = ParsedPath(
            kind=ResourceKind.TEMPLATE,
            origin=None,
            origin_explicit=False,
            path="intro",
            is_absolute=False,
        )

        with pytest.raises(AttributeError):
            parsed.path = "changed"


class TestResolvedPath:
    """Tests for ResolvedPath dataclass."""

    def test_create_resolved_path(self, tmp_path: Path):
        """Create ResolvedPath with all fields."""
        cfg_root = tmp_path / "lg-cfg"
        resource_path = cfg_root / "intro.tpl.md"

        resolved = ResolvedPath(
            kind=ResourceKind.TEMPLATE,
            scope_dir=tmp_path,
            scope_rel="",
            cfg_root=cfg_root,
            resource_path=resource_path,
            resource_rel="intro.tpl.md",
            canonical_id=None,
        )

        assert resolved.kind == ResourceKind.TEMPLATE
        assert resolved.scope_dir == tmp_path
        assert resolved.scope_rel == ""
        assert resolved.cfg_root == cfg_root
        assert resolved.resource_path == resource_path
        assert resolved.resource_rel == "intro.tpl.md"

    def test_create_resolved_section_with_canonical_id(self, tmp_path: Path):
        """Create ResolvedPath for section with canonical ID."""
        resolved = ResolvedPath(
            kind=ResourceKind.SECTION,
            scope_dir=tmp_path,
            scope_rel="apps/web",
            cfg_root=tmp_path / "apps" / "web" / "lg-cfg",
            resource_path=tmp_path / "apps" / "web" / "lg-cfg" / "sections.yaml",
            resource_rel="sections.yaml",
            canonical_id="web-src",
        )

        assert resolved.canonical_id == "web-src"

    def test_resolved_path_is_frozen(self, tmp_path: Path):
        """Verify ResolvedPath is immutable."""
        resolved = ResolvedPath(
            kind=ResourceKind.TEMPLATE,
            scope_dir=tmp_path,
            scope_rel="",
            cfg_root=tmp_path / "lg-cfg",
            resource_path=tmp_path / "lg-cfg" / "intro.tpl.md",
            resource_rel="intro.tpl.md",
        )

        with pytest.raises(AttributeError):
            resolved.resource_rel = "changed"


class TestDirectoryContext:
    """Tests for DirectoryContext dataclass."""

    def test_create_root_context(self, tmp_path: Path):
        """Create DirectoryContext for root scope."""
        ctx = DirectoryContext(
            origin="self",
            current_dir="",
            cfg_root=tmp_path / "lg-cfg",
        )

        assert ctx.origin == "self"
        assert ctx.current_dir == ""
        assert ctx.cfg_root == tmp_path / "lg-cfg"

    def test_create_nested_context(self, tmp_path: Path):
        """Create DirectoryContext for nested directory."""
        ctx = DirectoryContext(
            origin="apps/web",
            current_dir="docs/api",
            cfg_root=tmp_path / "apps" / "web" / "lg-cfg",
        )

        assert ctx.origin == "apps/web"
        assert ctx.current_dir == "docs/api"

    def test_repr_format(self, tmp_path: Path):
        """Verify repr format is readable."""
        ctx = DirectoryContext(
            origin="self",
            current_dir="docs",
            cfg_root=tmp_path / "lg-cfg",
        )

        repr_str = repr(ctx)
        assert "origin='self'" in repr_str
        assert "current_dir='docs'" in repr_str

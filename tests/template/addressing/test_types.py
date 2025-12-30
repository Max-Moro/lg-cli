"""
Tests for lg/template/addressing/types.py

Tests data types: ResourceConfig, ParsedPath, ResolvedPath, DirectoryContext.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lg.template.addressing import (
    ResourceConfig,
    ParsedPath,
    ResolvedPath,
    DirectoryContext,
)
from lg.template.common_placeholders.configs import (
    SECTION_CONFIG,
    TEMPLATE_CONFIG,
    CONTEXT_CONFIG,
)
from lg.template.md_placeholders.configs import (
    MARKDOWN_CONFIG,
    MARKDOWN_EXTERNAL_CONFIG,
)


class TestResourceConfig:
    """Tests for ResourceConfig dataclass."""

    def test_predefined_configs_exist(self):
        """Verify all predefined configs are defined."""
        assert SECTION_CONFIG.name == "section"
        assert TEMPLATE_CONFIG.name == "template"
        assert CONTEXT_CONFIG.name == "context"
        assert MARKDOWN_CONFIG.name == "markdown"
        assert MARKDOWN_EXTERNAL_CONFIG.name == "markdown_external"

    def test_config_extensions(self):
        """Verify configs have correct extensions."""
        assert SECTION_CONFIG.extension is None
        assert TEMPLATE_CONFIG.extension == ".tpl.md"
        assert CONTEXT_CONFIG.extension == ".ctx.md"
        assert MARKDOWN_CONFIG.extension == ".md"
        assert MARKDOWN_EXTERNAL_CONFIG.extension == ".md"

    def test_config_behaviors(self):
        """Verify configs have correct behavior flags."""
        assert SECTION_CONFIG.strip_md_syntax is False
        assert MARKDOWN_CONFIG.strip_md_syntax is True
        assert MARKDOWN_EXTERNAL_CONFIG.strip_md_syntax is True
        assert MARKDOWN_EXTERNAL_CONFIG.resolve_outside_cfg is True
        assert TEMPLATE_CONFIG.resolve_outside_cfg is False

    def test_custom_config(self):
        """Create custom ResourceConfig."""
        config = ResourceConfig(
            name="yaml",
            extension=".yaml",
        )
        assert config.name == "yaml"
        assert config.extension == ".yaml"
        assert config.strip_md_syntax is False
        assert config.resolve_outside_cfg is False


class TestParsedPath:
    """Tests for ParsedPath dataclass."""

    def test_create_simple_path(self):
        """Create ParsedPath with minimal required fields."""
        parsed = ParsedPath(
            config=TEMPLATE_CONFIG,
            origin=None,
            origin_explicit=False,
            path="intro",
            is_absolute=False,
        )

        assert parsed.config == TEMPLATE_CONFIG
        assert parsed.origin is None
        assert parsed.origin_explicit is False
        assert parsed.path == "intro"
        assert parsed.is_absolute is False

    def test_create_path_with_origin(self):
        """Create ParsedPath with explicit origin."""
        parsed = ParsedPath(
            config=SECTION_CONFIG,
            origin="apps/web",
            origin_explicit=True,
            path="web-src",
            is_absolute=False,
        )

        assert parsed.origin == "apps/web"
        assert parsed.origin_explicit is True

    def test_parsed_path_is_frozen(self):
        """Verify ParsedPath is immutable."""
        parsed = ParsedPath(
            config=TEMPLATE_CONFIG,
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
            config=TEMPLATE_CONFIG,
            scope_dir=tmp_path,
            scope_rel="",
            cfg_root=cfg_root,
            resource_path=resource_path,
            resource_rel="intro.tpl.md",
        )

        assert resolved.config == TEMPLATE_CONFIG
        assert resolved.scope_dir == tmp_path
        assert resolved.scope_rel == ""
        assert resolved.cfg_root == cfg_root
        assert resolved.resource_path == resource_path
        assert resolved.resource_rel == "intro.tpl.md"

    def test_create_resolved_section(self, tmp_path: Path):
        """Create ResolvedPath for section (resource_rel is canonical ID)."""
        resolved = ResolvedPath(
            config=SECTION_CONFIG,
            scope_dir=tmp_path,
            scope_rel="apps/web",
            cfg_root=tmp_path / "apps" / "web" / "lg-cfg",
            resource_path=tmp_path / "apps" / "web" / "lg-cfg" / "sections.yaml",
            resource_rel="web-src",  # For sections, resource_rel serves as canonical ID
        )

        assert resolved.resource_rel == "web-src"

    def test_resolved_path_is_frozen(self, tmp_path: Path):
        """Verify ResolvedPath is immutable."""
        resolved = ResolvedPath(
            config=TEMPLATE_CONFIG,
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

"""
Tests for lg/template/addressing/parser.py

Tests PathParser class for parsing path strings from placeholders.
"""

from __future__ import annotations

import pytest

from lg.template.addressing import PathParser, ParsedPath, ResourceKind, PathParseError


class TestPathParserBasic:
    """Basic parsing tests for PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_simple_template_path(self):
        """Parse simple template path without origin."""
        result = self.parser.parse("intro", ResourceKind.TEMPLATE)

        assert result.kind == ResourceKind.TEMPLATE
        assert result.path == "intro"
        assert result.origin is None
        assert result.origin_explicit is False
        assert result.is_absolute is False

    def test_parse_nested_path(self):
        """Parse path with directories."""
        result = self.parser.parse("common/header", ResourceKind.TEMPLATE)

        assert result.path == "common/header"
        assert result.is_absolute is False

    def test_parse_absolute_path(self):
        """Parse absolute path starting with /."""
        result = self.parser.parse("/common/header", ResourceKind.TEMPLATE)

        assert result.path == "common/header"  # Leading / stripped
        assert result.is_absolute is True

    def test_parse_path_with_parent_reference(self):
        """Parse path with ../ component."""
        result = self.parser.parse("../common/header", ResourceKind.TEMPLATE)

        assert result.path == "../common/header"
        assert result.is_absolute is False


class TestPathParserOrigin:
    """Tests for origin parsing in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_with_simple_origin(self):
        """Parse path with simple @origin:path format."""
        result = self.parser.parse("@apps/web:guide", ResourceKind.TEMPLATE)

        assert result.origin == "apps/web"
        assert result.origin_explicit is True
        assert result.path == "guide"

    def test_parse_with_self_origin(self):
        """Parse path with explicit @self:path format."""
        result = self.parser.parse("@self:intro", ResourceKind.TEMPLATE)

        assert result.origin == "self"
        assert result.origin_explicit is True
        assert result.path == "intro"

    def test_parse_with_root_origin(self):
        """Parse path with @/:path for root scope."""
        result = self.parser.parse("@/:common/header", ResourceKind.TEMPLATE)

        assert result.origin == "/"
        assert result.origin_explicit is True
        assert result.path == "common/header"

    def test_parse_with_bracket_origin(self):
        """Parse path with bracket origin @[origin]:path."""
        result = self.parser.parse("@[libs/core:v2]:api", ResourceKind.TEMPLATE)

        assert result.origin == "libs/core:v2"
        assert result.origin_explicit is True
        assert result.path == "api"

    def test_parse_origin_with_absolute_path(self):
        """Parse @origin:/absolute/path format."""
        result = self.parser.parse("@apps/web:/common/header", ResourceKind.TEMPLATE)

        assert result.origin == "apps/web"
        assert result.path == "common/header"
        assert result.is_absolute is True


class TestPathParserResourceKinds:
    """Tests for different resource kinds in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_section(self):
        """Parse section reference."""
        result = self.parser.parse_section("docs")

        assert result.kind == ResourceKind.SECTION
        assert result.path == "docs"

    def test_parse_template(self):
        """Parse template reference."""
        result = self.parser.parse_template("intro")

        assert result.kind == ResourceKind.TEMPLATE

    def test_parse_context(self):
        """Parse context reference."""
        result = self.parser.parse_context("main")

        assert result.kind == ResourceKind.CONTEXT

    def test_parse_markdown_with_at(self):
        """Parse markdown with @ (inside lg-cfg)."""
        result = self.parser.parse_markdown("self:budget", has_at=True)

        assert result.kind == ResourceKind.MARKDOWN
        assert result.origin == "self"

    def test_parse_markdown_without_at(self):
        """Parse markdown without @ (external, relative to repo)."""
        result = self.parser.parse_markdown("docs/api", has_at=False)

        assert result.kind == ResourceKind.MARKDOWN_EXTERNAL
        assert result.origin is None


class TestPathParserErrors:
    """Tests for error handling in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_error_on_empty_path(self):
        """Raise error on empty path."""
        with pytest.raises(PathParseError, match="Empty path"):
            self.parser.parse("", ResourceKind.TEMPLATE)

    def test_error_on_whitespace_only(self):
        """Raise error on whitespace-only path."""
        with pytest.raises(PathParseError, match="Empty path"):
            self.parser.parse("   ", ResourceKind.TEMPLATE)

    def test_error_on_invalid_origin_format(self):
        """Raise error on malformed origin."""
        with pytest.raises(PathParseError, match="Invalid origin format"):
            self.parser.parse("@invalid", ResourceKind.TEMPLATE)

    def test_error_on_empty_origin(self):
        """Raise error on empty origin in @:path."""
        with pytest.raises(PathParseError, match="Empty origin"):
            self.parser.parse("@:path", ResourceKind.TEMPLATE)

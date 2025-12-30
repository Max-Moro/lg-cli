"""
Tests for lg/template/addressing/parser.py

Tests PathParser class for parsing path strings from placeholders.
"""

from __future__ import annotations

import pytest

from lg.template.addressing import (
    PathParser,
    ParsedPath,
    PathParseError,
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


class TestPathParserBasic:
    """Basic parsing tests for PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_simple_template_path(self):
        """Parse simple template path without origin."""
        result = self.parser.parse("intro", TEMPLATE_CONFIG)

        assert result.config == TEMPLATE_CONFIG
        assert result.path == "intro"
        assert result.origin is None
        assert result.origin_explicit is False
        assert result.is_absolute is False

    def test_parse_nested_path(self):
        """Parse path with directories."""
        result = self.parser.parse("common/header", TEMPLATE_CONFIG)

        assert result.path == "common/header"
        assert result.is_absolute is False

    def test_parse_absolute_path(self):
        """Parse absolute path starting with /."""
        result = self.parser.parse("/common/header", TEMPLATE_CONFIG)

        assert result.path == "common/header"  # Leading / stripped
        assert result.is_absolute is True

    def test_parse_path_with_parent_reference(self):
        """Parse path with ../ component."""
        result = self.parser.parse("../common/header", TEMPLATE_CONFIG)

        assert result.path == "../common/header"
        assert result.is_absolute is False


class TestPathParserOrigin:
    """Tests for origin parsing in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_with_simple_origin(self):
        """Parse path with simple @origin:path format."""
        result = self.parser.parse("@apps/web:guide", TEMPLATE_CONFIG)

        assert result.origin == "apps/web"
        assert result.origin_explicit is True
        assert result.path == "guide"

    def test_parse_with_self_origin(self):
        """Parse path with explicit @self:path format."""
        result = self.parser.parse("@self:intro", TEMPLATE_CONFIG)

        assert result.origin == "self"
        assert result.origin_explicit is True
        assert result.path == "intro"

    def test_parse_with_root_origin(self):
        """Parse path with @/:path for root scope."""
        result = self.parser.parse("@/:common/header", TEMPLATE_CONFIG)

        assert result.origin == "/"
        assert result.origin_explicit is True
        assert result.path == "common/header"

    def test_parse_with_bracket_origin(self):
        """Parse path with bracket origin @[origin]:path."""
        result = self.parser.parse("@[libs/core:v2]:api", TEMPLATE_CONFIG)

        assert result.origin == "libs/core:v2"
        assert result.origin_explicit is True
        assert result.path == "api"

    def test_parse_origin_with_absolute_path(self):
        """Parse @origin:/absolute/path format."""
        result = self.parser.parse("@apps/web:/common/header", TEMPLATE_CONFIG)

        assert result.origin == "apps/web"
        assert result.path == "common/header"
        assert result.is_absolute is True


class TestPathParserWithConfigs:
    """Tests for different resource configs in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_parse_section(self):
        """Parse section reference."""
        result = self.parser.parse("docs", SECTION_CONFIG)

        assert result.config == SECTION_CONFIG
        assert result.path == "docs"

    def test_parse_template(self):
        """Parse template reference."""
        result = self.parser.parse("intro", TEMPLATE_CONFIG)

        assert result.config == TEMPLATE_CONFIG

    def test_parse_context(self):
        """Parse context reference."""
        result = self.parser.parse("main", CONTEXT_CONFIG)

        assert result.config == CONTEXT_CONFIG

    def test_parse_markdown_internal(self):
        """Parse markdown inside lg-cfg (with @origin:path)."""
        result = self.parser.parse("@self:budget", MARKDOWN_CONFIG)

        assert result.config == MARKDOWN_CONFIG
        assert result.origin == "self"

    def test_parse_markdown_external(self):
        """Parse markdown outside lg-cfg (external, relative to scope root)."""
        result = self.parser.parse("docs/api", MARKDOWN_EXTERNAL_CONFIG)

        assert result.config == MARKDOWN_EXTERNAL_CONFIG
        assert result.origin is None


class TestPathParserErrors:
    """Tests for error handling in PathParser."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = PathParser()

    def test_error_on_empty_path(self):
        """Raise error on empty path."""
        with pytest.raises(PathParseError, match="Empty path"):
            self.parser.parse("", TEMPLATE_CONFIG)

    def test_error_on_whitespace_only(self):
        """Raise error on whitespace-only path."""
        with pytest.raises(PathParseError, match="Empty path"):
            self.parser.parse("   ", TEMPLATE_CONFIG)

    def test_error_on_invalid_origin_format(self):
        """Raise error on malformed origin."""
        with pytest.raises(PathParseError, match="Invalid origin format"):
            self.parser.parse("@invalid", TEMPLATE_CONFIG)

    def test_error_on_empty_origin(self):
        """Raise error on empty origin in @:path."""
        with pytest.raises(PathParseError, match="Empty origin"):
            self.parser.parse("@:path", TEMPLATE_CONFIG)

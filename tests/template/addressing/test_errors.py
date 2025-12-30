"""
Tests for lg/template/addressing/errors.py

Tests exception classes and their formatting.
"""

from __future__ import annotations

import pytest

from lg.template.addressing import (
    AddressingError,
    PathParseError,
    PathResolutionError,
    ScopeNotFoundError,
    ParsedPath,
)
from lg.template.common_placeholders.configs import TEMPLATE_CONFIG


class TestPathParseError:
    """Tests for PathParseError exception."""

    def test_basic_error_message(self):
        """Test basic error message without position."""
        error = PathParseError(
            message="Invalid path format",
            raw_path="@invalid",
        )

        assert "Invalid path format" in str(error)
        assert "@invalid" in str(error)

    def test_error_with_position(self):
        """Test error message with position indicator."""
        error = PathParseError(
            message="Unexpected character",
            raw_path="path@wrong",
            position=4,
        )

        error_str = str(error)
        assert "at position 4" in error_str
        assert "path@wrong" in error_str

    def test_is_addressing_error(self):
        """Verify inheritance from AddressingError."""
        error = PathParseError(message="test", raw_path="test")
        assert isinstance(error, AddressingError)


class TestPathResolutionError:
    """Tests for PathResolutionError exception."""

    def test_basic_error_message(self):
        """Test basic resolution error."""
        error = PathResolutionError(message="Template not found")
        assert "Template not found" in str(error)

    def test_error_with_parsed_path(self):
        """Test error with parsed path context."""
        parsed = ParsedPath(
            config=TEMPLATE_CONFIG,
            origin="apps/web",
            origin_explicit=True,
            path="missing",
            is_absolute=False,
        )

        error = PathResolutionError(
            message="Resource not found",
            parsed=parsed,
        )

        error_str = str(error)
        assert "Resource not found" in error_str
        assert "Path: missing" in error_str
        assert "Origin: apps/web" in error_str

    def test_error_with_searched_paths(self):
        """Test error showing searched locations."""
        error = PathResolutionError(
            message="Template not found",
            searched_paths=[
                "/project/lg-cfg/intro.tpl.md",
                "/project/lg-cfg/common/intro.tpl.md",
            ],
        )

        error_str = str(error)
        assert "Searched:" in error_str
        assert "/project/lg-cfg/intro.tpl.md" in error_str

    def test_error_with_hint(self):
        """Test error with helpful hint."""
        error = PathResolutionError(
            message="Template not found",
            hint="Use absolute path '/intro' to search from lg-cfg/ root",
        )

        error_str = str(error)
        assert "Hint:" in error_str
        assert "absolute path" in error_str


class TestScopeNotFoundError:
    """Tests for ScopeNotFoundError exception."""

    def test_scope_not_found_message(self):
        """Test scope not found error formatting."""
        error = ScopeNotFoundError(
            message="Scope not found",
            scope_path="apps/mobile",
        )

        error_str = str(error)
        assert "apps/mobile" in error_str
        assert "lg-cfg/" in error_str
        assert "Hint:" in error_str

    def test_is_path_resolution_error(self):
        """Verify inheritance chain."""
        error = ScopeNotFoundError(message="test", scope_path="test")
        assert isinstance(error, PathResolutionError)
        assert isinstance(error, AddressingError)

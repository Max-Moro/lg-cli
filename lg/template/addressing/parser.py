"""
Path parser for the addressing system.

Parses path strings from placeholders into structured ParsedPath objects.
Does NOT perform resolution — only syntactic parsing.
"""

from __future__ import annotations

import re

from .types import ParsedPath, ResourceKind
from .errors import PathParseError


class PathParser:
    """
    Parser for path strings from placeholders.

    Transforms a path string into a structured ParsedPath.
    Does NOT perform resolution — only syntactic parsing.

    Note: Markdown-specific syntax (#anchor, ,params) is stripped but not parsed.
    These parameters are handled by MarkdownFileNode parser, not by addressing.
    """

    # Pattern for bracket origin: @[origin]:path
    _BRACKET_ORIGIN_PATTERN = re.compile(r'^\[([^\]]+)\]:(.+)$')

    # Pattern for simple origin: @origin:path
    _SIMPLE_ORIGIN_PATTERN = re.compile(r'^([^:]+):(.+)$')

    def parse(self, raw: str, kind: ResourceKind) -> ParsedPath:
        """
        Parse a path string.

        Args:
            raw: Raw string from placeholder (e.g., "@apps/web:docs/api")
            kind: Resource type (determines parsing rules)

        Returns:
            Structured ParsedPath

        Raises:
            PathParseError: On syntax error
        """
        if not raw or not raw.strip():
            raise PathParseError("Empty path", raw)

        raw = raw.strip()

        # For MARKDOWN_EXTERNAL, path is always relative to current scope
        if kind == ResourceKind.MARKDOWN_EXTERNAL:
            return self._parse_external_markdown(raw)

        # Check for @ prefix (explicit origin)
        if raw.startswith('@'):
            return self._parse_with_origin(raw[1:], kind)

        # No @ prefix — implicit origin from context
        return self._parse_without_origin(raw, kind)

    def parse_section(self, raw: str) -> ParsedPath:
        """Parse path to section."""
        return self.parse(raw, ResourceKind.SECTION)

    def parse_template(self, raw: str) -> ParsedPath:
        """Parse path to template (tpl:...)."""
        return self.parse(raw, ResourceKind.TEMPLATE)

    def parse_context(self, raw: str) -> ParsedPath:
        """Parse path to context (ctx:...)."""
        return self.parse(raw, ResourceKind.CONTEXT)

    def parse_markdown(self, raw: str, has_at: bool) -> ParsedPath:
        """
        Parse path to markdown (md:... or md@...:...).

        Determines kind as MARKDOWN or MARKDOWN_EXTERNAL
        based on presence of @.

        Args:
            raw: Path string after 'md:' or 'md@'
            has_at: True if @ was present (md@origin:path)
        """
        if has_at:
            # For md@origin:path, the raw string is "origin:path" (already without @)
            # We need to parse it as origin:path format
            return self._parse_with_origin(raw, ResourceKind.MARKDOWN)
        else:
            return self.parse(raw, ResourceKind.MARKDOWN_EXTERNAL)

    def _parse_with_origin(self, raw: str, kind: ResourceKind) -> ParsedPath:
        """
        Parse path with explicit origin (@origin:path or @[origin]:path).

        Args:
            raw: String after @ (e.g., "apps/web:docs/api" or "[apps/web:v2]:docs")
        """
        origin: str
        path_part: str
        is_bracket_form = False

        # Check for empty origin first (":path" case)
        if raw.startswith(':'):
            raise PathParseError("Empty origin after '@'", f"@{raw}")

        # Check for bracket form: [origin]:path
        bracket_match = self._BRACKET_ORIGIN_PATTERN.match(raw)
        if bracket_match:
            is_bracket_form = True
            origin = bracket_match.group(1)
            path_part = bracket_match.group(2)
        else:
            # Simple form: origin:path
            simple_match = self._SIMPLE_ORIGIN_PATTERN.match(raw)
            if not simple_match:
                raise PathParseError("Invalid origin format, expected 'origin:path'", f"@{raw}")
            origin = simple_match.group(1)
            path_part = simple_match.group(2)

        if not origin:
            if is_bracket_form:
                raise PathParseError("Empty origin in bracket form '@[]:path'", f"@{raw}")
            else:
                raise PathParseError("Empty origin in '@origin:path'", f"@{raw}")

        path = self._extract_base_path(path_part, kind)
        is_absolute = path.startswith('/')
        normalized_path = path.lstrip('/') if is_absolute else path

        return ParsedPath(
            kind=kind,
            origin=origin,
            origin_explicit=True,
            path=normalized_path,
            is_absolute=is_absolute,
        )

    def _parse_without_origin(self, raw: str, kind: ResourceKind) -> ParsedPath:
        """Parse path without origin (implicit from context)."""
        path = self._extract_base_path(raw, kind)
        is_absolute = path.startswith('/')
        normalized_path = path.lstrip('/') if is_absolute else path

        return ParsedPath(
            kind=kind,
            origin=None,
            origin_explicit=False,
            path=normalized_path,
            is_absolute=is_absolute,
        )

    def _parse_external_markdown(self, raw: str) -> ParsedPath:
        """Parse external markdown path (relative to current scope)."""
        path = self._extract_base_path(raw, ResourceKind.MARKDOWN_EXTERNAL)

        # External markdown paths are always relative to current scope
        # Leading / is optional and doesn't change semantics
        normalized_path = path.lstrip('/')

        return ParsedPath(
            kind=ResourceKind.MARKDOWN_EXTERNAL,
            origin=None,
            origin_explicit=False,
            path=normalized_path,
            is_absolute=False,  # Always relative to current scope
        )

    def _extract_base_path(self, raw: str, kind: ResourceKind) -> str:
        """
        Extract base path from raw string.

        For MD resources, strips MD-specific syntax (#anchor, ,params).
        MD-specific parameters are handled by MarkdownFileNode, not by addressing.

        For other resources, returns raw as-is.

        Args:
            raw: Raw path string
            kind: Resource kind

        Returns:
            Base path without MD-specific decorations
        """
        if kind not in (ResourceKind.MARKDOWN, ResourceKind.MARKDOWN_EXTERNAL):
            return raw

        # For MD: extract path before # or ,
        # Examples:
        #   "docs/api#section,level:2" -> "docs/api"
        #   "README.md" -> "README.md"
        for separator in ('#', ','):
            if separator in raw:
                return raw.split(separator, 1)[0].strip()

        return raw.strip()


__all__ = ["PathParser"]

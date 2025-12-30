"""
Path parser for the addressing system.

Parses path strings from placeholders into structured ParsedPath objects.
Does NOT perform resolution — only syntactic parsing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from .types import ParsedPath, ResourceKind
from .errors import PathParseError


class PathParser:
    """
    Parser for path strings from placeholders.

    Transforms a path string into a structured ParsedPath.
    Does NOT perform resolution — only syntactic parsing.
    """

    # Pattern for bracket origin: @[origin]:path
    _BRACKET_ORIGIN_PATTERN = re.compile(r'^\[([^\]]+)\]:(.+)$')

    # Pattern for simple origin: @origin:path
    _SIMPLE_ORIGIN_PATTERN = re.compile(r'^([^:]+):(.+)$')

    # Pattern for md parameters: path,param:value,param:value
    _MD_PARAMS_PATTERN = re.compile(r'^([^,#]+)(#[^,]+)?((?:,[^,]+)*)$')

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

        # For MARKDOWN_EXTERNAL, path is always relative to repo root
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

        # Check for empty origin first (":path" case)
        if raw.startswith(':'):
            raise PathParseError("Empty origin", f"@{raw}")

        # Check for bracket form: [origin]:path
        bracket_match = self._BRACKET_ORIGIN_PATTERN.match(raw)
        if bracket_match:
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
            raise PathParseError("Empty origin", f"@{raw}")

        # Parse path and parameters
        path, anchor, params = self._parse_path_and_params(path_part, kind)
        is_absolute = path.startswith('/')
        normalized_path = path.lstrip('/') if is_absolute else path

        return ParsedPath(
            kind=kind,
            origin=origin,
            origin_explicit=True,
            path=normalized_path,
            is_absolute=is_absolute,
            anchor=anchor,
            parameters=params,
        )

    def _parse_without_origin(self, raw: str, kind: ResourceKind) -> ParsedPath:
        """Parse path without origin (implicit from context)."""
        path, anchor, params = self._parse_path_and_params(raw, kind)
        is_absolute = path.startswith('/')
        normalized_path = path.lstrip('/') if is_absolute else path

        return ParsedPath(
            kind=kind,
            origin=None,
            origin_explicit=False,
            path=normalized_path,
            is_absolute=is_absolute,
            anchor=anchor,
            parameters=params,
        )

    def _parse_external_markdown(self, raw: str) -> ParsedPath:
        """Parse external markdown path (relative to repo root)."""
        path, anchor, params = self._parse_path_and_params(raw, ResourceKind.MARKDOWN_EXTERNAL)

        # External markdown paths are always relative to repo root
        # Leading / is optional and doesn't change semantics
        normalized_path = path.lstrip('/')

        return ParsedPath(
            kind=ResourceKind.MARKDOWN_EXTERNAL,
            origin=None,
            origin_explicit=False,
            path=normalized_path,
            is_absolute=False,  # Always relative to repo root
            anchor=anchor,
            parameters=params,
        )

    def _parse_path_and_params(
        self,
        raw: str,
        kind: ResourceKind
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        Parse path with optional anchor and parameters.

        For md placeholders: path#anchor,param:value,param:value
        For others: just path

        Returns:
            (path, anchor, parameters)
        """
        if kind not in (ResourceKind.MARKDOWN, ResourceKind.MARKDOWN_EXTERNAL):
            # No parameters for non-md resources
            return raw, None, {}

        # Parse md format: path#anchor,param:value,...
        match = self._MD_PARAMS_PATTERN.match(raw)
        if not match:
            return raw, None, {}

        path = match.group(1).strip()
        anchor_part = match.group(2)  # #anchor or None
        params_part = match.group(3)  # ,param:value,... or ""

        anchor = anchor_part[1:].strip() if anchor_part else None
        params = self._parse_md_parameters(params_part) if params_part else {}

        return path, anchor, params

    def _parse_md_parameters(self, params_str: str) -> Dict[str, Any]:
        """
        Parse md placeholder parameters.

        Format: ,param:value,param:value,...

        Returns:
            Dictionary of parameters
        """
        params: Dict[str, Any] = {}
        if not params_str:
            return params

        # Split by comma, skip first empty element
        parts = params_str.split(',')[1:]

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if ':' not in part:
                raise PathParseError(f"Invalid parameter format '{part}', expected 'name:value'", params_str)

            name, value = part.split(':', 1)
            name = name.strip()
            value = value.strip()

            # Type conversion
            params[name] = self._convert_param_value(name, value)

        return params

    def _convert_param_value(self, name: str, value: str) -> Any:
        """Convert parameter value to appropriate type."""
        # Boolean parameters
        if name in ('strip_h1',):
            return value.lower() in ('true', '1', 'yes')

        # Integer parameters
        if name in ('level',):
            try:
                return int(value)
            except ValueError:
                raise PathParseError(f"Parameter '{name}' must be integer, got '{value}'", value)

        # String parameters (if, anchor, etc.)
        return value


__all__ = ["PathParser"]

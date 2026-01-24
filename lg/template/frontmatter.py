"""
Frontmatter parser for context files.

Parses YAML frontmatter from .ctx.md files for adaptive system configuration.
Frontmatter is used to include additional sections for mode-set/tag-set resolution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ruamel.yaml import YAML

_yaml = YAML(typ="safe")

# Pattern for YAML frontmatter: starts with ---, ends with ---
_FRONTMATTER_PATTERN = re.compile(
    r'^---\s*\n(.*?)\n---\s*\n?',
    re.DOTALL
)


@dataclass
class ContextFrontmatter:
    """
    Parsed frontmatter from a context file.

    Contains configuration that affects adaptive model resolution
    but is not rendered in the final output.
    """
    include: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ContextFrontmatter:
        """Create from parsed YAML dictionary."""
        include = data.get("include", [])
        if isinstance(include, str):
            include = [include]
        return cls(include=list(include))

    def is_empty(self) -> bool:
        """Check if frontmatter has no meaningful content."""
        return not self.include


def parse_frontmatter(text: str) -> Tuple[Optional[ContextFrontmatter], str]:
    """
    Parse YAML frontmatter from context file text.

    Args:
        text: Full text of the context file

    Returns:
        Tuple of (frontmatter, remaining_text):
        - frontmatter: Parsed ContextFrontmatter or None if no frontmatter
        - remaining_text: Text with frontmatter removed

    Examples:
        >>> fm, text = parse_frontmatter("---\\ninclude: [base]\\n---\\n# Content")
        >>> fm.include
        ['base']
        >>> text
        '# Content'
    """
    if not text.startswith('---'):
        return None, text

    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        # Starts with --- but no closing ---, treat as no frontmatter
        return None, text

    yaml_content = match.group(1)
    remaining_text = text[match.end():]

    try:
        data = _yaml.load(yaml_content)
        if data is None:
            # Empty frontmatter
            return ContextFrontmatter(), remaining_text
        if not isinstance(data, dict):
            # Invalid frontmatter format, ignore it
            return None, text

        frontmatter = ContextFrontmatter.from_dict(data)
        return frontmatter, remaining_text

    except Exception:
        # YAML parsing error, treat as no frontmatter
        return None, text


def strip_frontmatter(text: str) -> str:
    """
    Remove frontmatter from text, returning only content.

    Args:
        text: Full text possibly containing frontmatter

    Returns:
        Text with frontmatter removed
    """
    _, remaining = parse_frontmatter(text)
    return remaining


def has_frontmatter(text: str) -> bool:
    """
    Check if text contains valid frontmatter.

    Args:
        text: Text to check

    Returns:
        True if text has valid YAML frontmatter
    """
    frontmatter, _ = parse_frontmatter(text)
    return frontmatter is not None


__all__ = [
    "ContextFrontmatter",
    "parse_frontmatter",
    "strip_frontmatter",
    "has_frontmatter",
]

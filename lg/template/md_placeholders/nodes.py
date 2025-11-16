"""
AST nodes for Markdown placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..nodes import TemplateNode


@dataclass(frozen=True)
class MarkdownFileNode(TemplateNode):
    """
    Placeholder for direct Markdown file inclusion ${md:path} or ${md:path#section}.

    Represents a reference to a Markdown file (or set of files via globs)
    that should be processed and included in the current location.

    Attributes:
        path: File path relative to scope (e.g., "docs/api" or "*.md")
        origin: Scope for addressed references ("self", path to lg-cfg or None)

        # Heading processing parameters
        heading_level: Explicitly set heading level (None for auto-detection)
        strip_h1: Flag for H1 removal (None for auto-detection)

        # Partial inclusion
        anchor: Anchor for including only specific section

        # Conditional inclusion
        condition: Condition text for checking tags/modes

        # Glob support
        is_glob: Flag indicating path contains glob pattern
    """
    path: str                      # File path (may contain globs)
    origin: Optional[str] = None   # "self" or path to scope

    # Heading processing parameters (automatic or explicit)
    heading_level: Optional[int] = None    # Explicit heading level
    strip_h1: Optional[bool] = None        # Flag for H1 removal

    # Partial inclusion
    anchor: Optional[str] = None           # Anchor for section inclusion

    # Conditional inclusion
    condition: Optional[str] = None        # Condition to check

    # Glob support
    is_glob: bool = False                  # Flag for glob pattern

    def canon_key(self) -> str:
        """
        Returns canonical key for caching and deduplication.

        Returns:
            String like "md:path" or "md@origin:path" with parameters
        """
        parts = ["md"]

        # Add origin if specified
        if self.origin and self.origin != "self":
            parts.append(f"@{self.origin}")

        parts.append(f":{self.path}")

        # Add anchor if specified
        if self.anchor:
            parts.append(f"#{self.anchor}")

        # Add parameters if specified
        params = []
        if self.heading_level is not None:
            params.append(f"level:{self.heading_level}")
        if self.strip_h1 is not None:
            params.append(f"strip_h1:{str(self.strip_h1).lower()}")
        if self.condition:
            params.append(f"if:{self.condition}")

        if params:
            parts.append("," + ",".join(params))

        return "".join(parts)


__all__ = ["MarkdownFileNode"]

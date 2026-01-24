"""
Plugin for processing Markdown placeholders.

Handles:
- ${md:path} - direct inclusion of Markdown file
- ${md:path#anchor} - inclusion of section by heading
- ${md:path,level:3,strip_h1:true} - inclusion with parameters
- ${md@origin:path} - addressed references to files in other scopes
- ${md:docs/*} - globs for including multiple files
- ${md:path,if:tag:condition} - conditional inclusions
"""

from __future__ import annotations

from .nodes import MarkdownFileNode

__all__ = ["MarkdownFileNode"]

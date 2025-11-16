"""
Plugin for processing basic section and template placeholders.

Handles:
- ${section_name} - section insertion
- ${tpl:template_name} - template inclusion
- ${ctx:context_name} - context inclusion
- Addressed references @origin:name for cross-scope inclusions
"""

from __future__ import annotations

from .nodes import SectionNode, IncludeNode
from .plugin import CommonPlaceholdersPlugin

__all__ = ["CommonPlaceholdersPlugin", "SectionNode", "IncludeNode"]
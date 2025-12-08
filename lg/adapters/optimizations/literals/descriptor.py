"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .categories import LiteralPattern


@dataclass
class LanguageLiteralDescriptor:
    """
    Declarative description of literal patterns in a language.

    Languages provide this descriptor to define how their literals
    should be recognized and processed.
    """

    # List of literal patterns in priority order
    patterns: List[LiteralPattern]

    # Additional factory wrappers for nested detection (not patterns themselves)
    # Example: ["Map.entry"] for Java - not optimized directly but needs DFS detection
    nested_factory_wrappers: List[str] = field(default_factory=list)

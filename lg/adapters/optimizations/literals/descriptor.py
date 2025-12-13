"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .patterns import (
    LiteralProfile,
)


@dataclass
class LanguageLiteralDescriptor:
    """
    Declarative description of literal patterns in a language.

    Languages provide this descriptor to define how their literals
    should be recognized and processed.

    All literal profiles (strings, sequences, mappings, factories, and block initializations)
    are unified in a single profiles list for simplified single-pass processing.
    """

    # All literal profiles (strings, sequences, mappings, factories, blocks)
    # Unified collection of all profile types for flexible processing
    profiles: List[LiteralProfile] = field(default_factory=list)

    # Additional factory wrappers for nested detection (not patterns themselves)
    # Example: ["Map.entry"] for Java - not optimized directly but needs DFS detection
    nested_factory_wrappers: List[str] = field(default_factory=list)


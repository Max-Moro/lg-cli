"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .categories import LiteralPattern
from .patterns import (
    LanguageSyntaxFlags,
    StringProfile,
    SequenceProfile,
    MappingProfile,
)


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

    # Language-specific syntax flags
    syntax: Optional[LanguageSyntaxFlags] = None

    # ============= Profile-based configuration (v2) =============
    # These fields define literals using typed profiles instead of flat LiteralPattern.
    # All fields are optional and default to empty. When profiles are present,
    # they should be converted to LiteralPattern via to_patterns() method.

    # String literal profiles (can have multiple: regular, template, raw, etc.)
    string_profiles: List[StringProfile] = field(default_factory=list)

    # Sequence literal profiles (lists, arrays, tuples, sets, etc.)
    sequence_profiles: List[SequenceProfile] = field(default_factory=list)

    # Mapping literal profiles (dicts, maps, objects, etc.)
    mapping_profiles: List[MappingProfile] = field(default_factory=list)

"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .patterns import (
    LanguageSyntaxFlags,
    StringProfile,
    SequenceProfile,
    MappingProfile,
    FactoryProfile,
    BlockInitProfile,
)


@dataclass
class LanguageLiteralDescriptor:
    """
    Declarative description of literal patterns in a language.

    Languages provide this descriptor to define how their literals
    should be recognized and processed.
    """

    # Additional factory wrappers for nested detection (not patterns themselves)
    # Example: ["Map.entry"] for Java - not optimized directly but needs DFS detection
    nested_factory_wrappers: List[str] = field(default_factory=list)

    # Language-specific syntax flags
    syntax: Optional[LanguageSyntaxFlags] = None

    # ============= Profile-based configuration =============
    # These fields define literals using typed profiles (StringProfile, SequenceProfile, etc.).
    # All fields are optional and default to empty.

    # String literal profiles (can have multiple: regular, template, raw, etc.)
    string_profiles: List[StringProfile] = field(default_factory=list)

    # Sequence literal profiles (lists, arrays, tuples, sets, etc.)
    sequence_profiles: List[SequenceProfile] = field(default_factory=list)

    # Mapping literal profiles (dicts, maps, objects, etc.)
    mapping_profiles: List[MappingProfile] = field(default_factory=list)

    # Factory method/macro profiles (List.of(), vec![], mapOf(), etc.)
    factory_profiles: List[FactoryProfile] = field(default_factory=list)

    # Block initialization profiles (Java double-brace, Rust HashMap chains, etc.)
    block_init_profiles: List[BlockInitProfile] = field(default_factory=list)


"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .categories import LiteralPattern, LiteralCategory
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

    # List of literal patterns in priority order (v1 - legacy)
    # Use underscore to make it "private", access via @property patterns
    _patterns: List[LiteralPattern] = field(default_factory=list)

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

    def to_patterns(self) -> List[LiteralPattern]:
        """
        Convert profile-based configuration to LiteralPattern instances.

        This method provides backward compatibility by converting the new
        typed profiles (StringProfile, SequenceProfile, MappingProfile) into
        the legacy LiteralPattern format.

        Also includes legacy _patterns for gradual migration support.

        Returns:
            List of LiteralPattern instances sorted by priority (descending)
        """
        patterns: List[LiteralPattern] = []

        # Convert StringProfile instances
        for profile in self.string_profiles:
            pattern = LiteralPattern(
                category=LiteralCategory.STRING,
                query=profile.query,
                opening=profile.opening,
                closing=profile.closing,
                placeholder_position=profile.placeholder_position,
                placeholder_template=profile.placeholder_template,
                preserve_whitespace=profile.preserve_whitespace,
                interpolation_markers=profile.interpolation_markers,
                interpolation_active=profile.interpolation_active,
                priority=profile.priority,
                comment_name=profile.comment_name,
            )
            patterns.append(pattern)

        # Convert SequenceProfile instances
        for profile in self.sequence_profiles:
            pattern = LiteralPattern(
                category=LiteralCategory.SEQUENCE,
                query=profile.query,
                opening=profile.opening,
                closing=profile.closing,
                separator=profile.separator,
                placeholder_position=profile.placeholder_position,
                placeholder_template=profile.placeholder_template,
                min_elements=profile.min_elements,
                priority=profile.priority,
                comment_name=profile.comment_name,
                requires_ast_extraction=profile.requires_ast_extraction,
            )
            patterns.append(pattern)

        # Convert MappingProfile instances
        for profile in self.mapping_profiles:
            pattern = LiteralPattern(
                category=LiteralCategory.MAPPING,
                query=profile.query,
                opening=profile.opening,
                closing=profile.closing,
                separator=profile.separator,
                kv_separator=profile.kv_separator,
                placeholder_position=profile.placeholder_position,
                placeholder_template=profile.placeholder_template,
                min_elements=profile.min_elements,
                priority=profile.priority,
                comment_name=profile.comment_name,
                preserve_all_keys=profile.preserve_all_keys,
            )
            patterns.append(pattern)

        # Add legacy patterns for gradual migration
        # This ensures backward compatibility during v1→v2 transition
        patterns.extend(self._patterns)

        # Sort by priority (descending) to maintain priority-based matching
        patterns.sort(key=lambda p: p.priority, reverse=True)

        return patterns

    @property
    def patterns(self) -> List[LiteralPattern]:
        """
        Get literal patterns for this language.

        Returns profile-based patterns if any profiles are defined,
        otherwise returns the legacy patterns list.

        This property provides backward compatibility during the v1→v2 migration.
        """
        # Check if any v2 profiles are defined
        has_profiles = (
            len(self.string_profiles) > 0 or
            len(self.sequence_profiles) > 0 or
            len(self.mapping_profiles) > 0
        )

        if has_profiles:
            # Use v2 profile-based configuration
            return self.to_patterns()
        else:
            # Fall back to v1 legacy patterns
            return self._patterns

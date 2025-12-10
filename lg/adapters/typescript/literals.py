"""
TypeScript language descriptor for literal optimization.

Extends JavaScript with TypeScript-specific type literals.
"""

from __future__ import annotations

from ..javascript.literals import (
    JS_TEMPLATE_STRING_PROFILE,
    JS_STRING_PROFILE,
    JS_REGEX_PROFILE,
    JS_ARRAY_PROFILE,
    JS_OBJECT_PROFILE,
)
from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    MappingProfile,
    LanguageSyntaxFlags,
)

# ============= TypeScript literal profiles (v2) =============

# TypeScript-specific: object type mapping profile (interfaces, type literals)
TS_OBJECT_TYPE_PROFILE = MappingProfile(
    query="(object_type) @lit",
    opening="{",
    closing="}",
    separator=";",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…": "…"',
    min_elements=1,
)


def create_typescript_descriptor() -> LanguageLiteralDescriptor:
    """
    Create TypeScript language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for TypeScript
    """
    return LanguageLiteralDescriptor(
        # Language syntax flags (same as JavaScript)
        syntax=LanguageSyntaxFlags(
            single_line_comment="//",
            block_comment_open="/*",
            block_comment_close="*/",
            supports_raw_strings=False,          # TypeScript has no raw strings
            supports_template_strings=True,      # TypeScript has template strings ``
            supports_multiline_strings=True,     # Template strings can be multiline
            factory_wrappers=[],                 # TypeScript has no factory methods
            supports_block_init=False,           # TypeScript has no block init
            supports_ast_sequences=False,        # TypeScript has no concatenated strings
        ),

        # String profiles (inherited from JavaScript)
        string_profiles=[
            JS_TEMPLATE_STRING_PROFILE,  # Higher priority - check first
            JS_STRING_PROFILE,
            JS_REGEX_PROFILE,
        ],

        # Sequence profiles (inherited from JavaScript)
        sequence_profiles=[JS_ARRAY_PROFILE],

        # Mapping profiles (JavaScript + TypeScript-specific)
        mapping_profiles=[
            TS_OBJECT_TYPE_PROFILE,  # TypeScript-specific object types
            JS_OBJECT_PROFILE,       # JavaScript objects
        ],
    )

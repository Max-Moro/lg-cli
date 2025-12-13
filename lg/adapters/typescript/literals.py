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
)

# TypeScript literal profiles

# TypeScript-specific: object type mapping profile (interfaces, type literals)
TS_OBJECT_TYPE_PROFILE = MappingProfile(
    query="(object_type) @lit",
    opening="{",
    closing="}",
    separator=";",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…": "…"',
)


def create_typescript_descriptor() -> LanguageLiteralDescriptor:
    """
    Create TypeScript language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for TypeScript
    """
    return LanguageLiteralDescriptor(
        profiles=[
            # String profiles (inherited from JavaScript)
            JS_TEMPLATE_STRING_PROFILE,  # Template strings (backticks with interpolation)
            JS_STRING_PROFILE,            # Regular strings (single and double quotes)
            JS_REGEX_PROFILE,             # Regex literals

            # Sequence profiles (inherited from JavaScript)
            JS_ARRAY_PROFILE,

            # Mapping profiles (JavaScript + TypeScript-specific)
            TS_OBJECT_TYPE_PROFILE,  # TypeScript-specific object types
            JS_OBJECT_PROFILE,       # JavaScript objects
        ]
    )

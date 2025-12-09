"""
TypeScript language descriptor for literal optimization.

Extends JavaScript with TypeScript-specific type literals.
"""

from __future__ import annotations

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)
from ..javascript.literals import (
    JS_TEMPLATE_STRING,
    JS_STRING,
    JS_REGEX,
    JS_ARRAY,
    JS_OBJECT,
)


# TypeScript-specific: object types (interfaces, type literals)
TS_OBJECT_TYPE = LiteralPattern(
    category=LiteralCategory.MAPPING,
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
        _patterns=[
            JS_TEMPLATE_STRING,  # Higher priority - check first
            JS_STRING,
            JS_REGEX,
            JS_ARRAY,
            TS_OBJECT_TYPE,  # TypeScript-specific
            JS_OBJECT,
        ]
    )

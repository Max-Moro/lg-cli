"""
TypeScript language descriptor for literal optimization v2.

Extends JavaScript with TypeScript-specific type literals.
"""

from __future__ import annotations

from ..optimizations.literals_v2 import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)
from ..javascript.literals_v2 import (
    JS_TEMPLATE_STRING,
    JS_STRING,
    JS_REGEX,
    JS_ARRAY,
    JS_OBJECT,
)


# TypeScript-specific: object types (interfaces, type literals)
TS_OBJECT_TYPE = LiteralPattern(
    category=LiteralCategory.MAPPING,
    tree_sitter_types=["object_type"],
    opening="{",
    closing="}",
    separator=";",  # TypeScript object types use semicolons
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
        language="typescript",
        patterns=[
            JS_TEMPLATE_STRING,  # Higher priority - check first
            JS_STRING,
            JS_REGEX,
            JS_ARRAY,
            TS_OBJECT_TYPE,  # TypeScript-specific
            JS_OBJECT,
        ],
        preserve_comments=True,
        respect_strings=True,
        min_literal_tokens=20,
    )


# Convenience: pre-built descriptor instance
TYPESCRIPT_DESCRIPTOR = create_typescript_descriptor()

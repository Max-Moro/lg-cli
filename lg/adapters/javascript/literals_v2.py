"""
JavaScript language descriptor for literal optimization v2.

Defines patterns for JavaScript literals: strings, template strings, arrays, objects.
Also used as base for TypeScript.
"""

from __future__ import annotations

from ..optimizations.literals_v2 import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_string_opening(text: str) -> str:
    """
    Detect JavaScript string opening delimiter.

    Handles: "", '', ``
    """
    stripped = text.strip()

    if stripped.startswith('`'):
        return '`'
    if stripped.startswith('"'):
        return '"'
    if stripped.startswith("'"):
        return "'"

    # Fallback
    return '"'


def _detect_string_closing(text: str) -> str:
    """
    Detect JavaScript string closing delimiter.
    """
    stripped = text.strip()

    if stripped.endswith('`'):
        return '`'
    if stripped.endswith('"'):
        return '"'
    if stripped.endswith("'"):
        return "'"

    # Fallback
    return '"'


# JavaScript literal patterns
JS_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["string"],
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

JS_TEMPLATE_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["template_string"],
    opening="`",
    closing="`",
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    # Template strings preserve whitespace
    preserve_whitespace=True,
    # Higher priority to match before generic string
    priority=10,
    # Template strings support ${...} interpolation
    interpolation_markers=[("$", "{", "}")],
)

JS_REGEX = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["regex"],
    opening="/",
    closing="/",  # Note: flags come after, handled specially
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

JS_ARRAY = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    tree_sitter_types=["array"],
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

JS_OBJECT = LiteralPattern(
    category=LiteralCategory.MAPPING,
    tree_sitter_types=["object"],
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…": "…"',
    min_elements=1,
    comment_name="object",
)


def create_javascript_descriptor() -> LanguageLiteralDescriptor:
    """
    Create JavaScript language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for JavaScript
    """
    return LanguageLiteralDescriptor(
        language="javascript",
        patterns=[
            JS_TEMPLATE_STRING,  # Higher priority - check first
            JS_STRING,
            JS_REGEX,
            JS_ARRAY,
            JS_OBJECT,
        ],
        preserve_comments=True,
        respect_strings=True,
        min_literal_tokens=20,
    )


# Convenience: pre-built descriptor instance
JAVASCRIPT_DESCRIPTOR = create_javascript_descriptor()

"""
JavaScript language descriptor for literal optimization.

Defines patterns for JavaScript literals: strings, template strings, arrays, objects.
Also used as base for TypeScript.
"""

from __future__ import annotations

from ..optimizations.literals import (
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
    query="(string) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

JS_TEMPLATE_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    query="(template_string) @lit",
    opening="`",
    closing="`",
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    preserve_whitespace=True,
    priority=10,
    interpolation_markers=[("$", "{", "}")],
)

JS_REGEX = LiteralPattern(
    category=LiteralCategory.STRING,
    query="(regex) @lit",
    opening="/",
    closing="/",
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

JS_ARRAY = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    query="(array) @lit",
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
    query="(object) @lit",
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
        _patterns=[
            JS_TEMPLATE_STRING,  # Higher priority - check first
            JS_STRING,
            JS_REGEX,
            JS_ARRAY,
            JS_OBJECT,
        ]
    )

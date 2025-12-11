"""
JavaScript language descriptor for literal optimization.

Defines patterns for JavaScript literals: strings, template strings, arrays, objects.
Also used as base for TypeScript.
"""

from __future__ import annotations

from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    SequenceProfile,
    MappingProfile,
    LanguageSyntaxFlags,
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


# JavaScript literal profiles

# Regular string profile (single and double quotes)
JS_STRING_PROFILE = StringProfile(
    query="(string) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

# Template string profile (backticks with interpolation)
JS_TEMPLATE_STRING_PROFILE = StringProfile(
    query="(template_string) @lit",
    opening="`",
    closing="`",
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    preserve_whitespace=True,
    interpolation_markers=[("$", "{", "}")],
)

# Regex profile
JS_REGEX_PROFILE = StringProfile(
    query="(regex) @lit",
    opening="/",
    closing="/",
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
)

# Array sequence profile
JS_ARRAY_PROFILE = SequenceProfile(
    query="(array) @lit",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

# Object mapping profile
JS_OBJECT_PROFILE = MappingProfile(
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
        # Language syntax flags
        syntax=LanguageSyntaxFlags(
            single_line_comment="//",
            block_comment_open="/*",
            block_comment_close="*/",
            supports_raw_strings=False,          # JavaScript has no raw strings
            supports_template_strings=True,      # JavaScript has template strings ``
            supports_multiline_strings=True,     # Template strings can be multiline
            factory_wrappers=[],                 # JavaScript has no factory methods
            supports_block_init=False,           # JavaScript has no block init
            supports_ast_sequences=False,        # JavaScript has no concatenated strings
        ),

        # String profiles
        string_profiles=[
            JS_TEMPLATE_STRING_PROFILE,  # Template strings (backticks with interpolation)
            JS_STRING_PROFILE,            # Regular strings (single and double quotes)
            JS_REGEX_PROFILE,             # Regex literals
        ],

        # Sequence profiles
        sequence_profiles=[JS_ARRAY_PROFILE],

        # Mapping profiles
        mapping_profiles=[JS_OBJECT_PROFILE],
    )

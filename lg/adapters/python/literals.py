"""
Python language descriptor for literal optimization.

Defines patterns for Python literals: strings, lists, tuples, dicts, sets.
"""

from __future__ import annotations

import re

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    LanguageSyntaxFlags,
)


def _detect_string_opening(text: str) -> str:
    """
    Detect Python string opening delimiter.

    Handles: "", '', \"""\""", ''', f"", r"", b"", fr"", rf"", etc.
    """
    stripped = text.strip()

    # Check for prefixes (f, r, b, u, fr, rf, br, rb)
    prefix_match = re.match(r'^([fFrRbBuU]{0,2})', stripped)
    prefix = prefix_match.group(1) if prefix_match else ""

    rest = stripped[len(prefix):]

    # Check for triple quotes first
    if rest.startswith('"""'):
        return f'{prefix}"""'
    if rest.startswith("'''"):
        return f"{prefix}'''"

    # Single quotes
    if rest.startswith('"'):
        return f'{prefix}"'
    if rest.startswith("'"):
        return f"{prefix}'"

    # Fallback
    return '"'


def _detect_string_closing(text: str) -> str:
    """
    Detect Python string closing delimiter.

    Matches the opening delimiter style.
    """
    stripped = text.strip()

    # Check for triple quotes at end
    if stripped.endswith('"""'):
        return '"""'
    if stripped.endswith("'''"):
        return "'''"

    # Single quotes
    if stripped.endswith('"'):
        return '"'
    if stripped.endswith("'"):
        return "'"

    # Fallback
    return '"'


def _is_f_string(opening: str, content: str) -> bool:
    """
    Check if string is an f-string (supports {} interpolation).

    Args:
        opening: String opening delimiter with f/F prefix
        content: String content (not used, signature required by pattern)

    Returns:
        True if the string is an f-string (opening contains f or F)
    """
    return 'f' in opening.lower() or 'F' in opening


# Python literal patterns

# String profile (v2)
PYTHON_STRING_PROFILE = StringProfile(
    query="(string) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[("", "{", "}")],
    interpolation_active=_is_f_string,
    preserve_whitespace=False,
    priority=0,
    comment_name=None,
)

# Legacy LiteralPattern (to be removed after full migration)
PYTHON_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    query="(string) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    # f-strings use {...} for interpolation
    # Callback checks if string is f-string before applying interpolation markers
    interpolation_markers=[("", "{", "}")],
    interpolation_active=_is_f_string,
)

PYTHON_LIST = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    query="(list) @lit",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

PYTHON_TUPLE = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    query="(tuple) @lit",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="tuple",
)

PYTHON_DICT = LiteralPattern(
    category=LiteralCategory.MAPPING,
    query="(dictionary) @lit",
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…": "…"',
    min_elements=1,
    comment_name="object",
)

PYTHON_SET = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    query="(set) @lit",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="set",
)


def create_python_descriptor() -> LanguageLiteralDescriptor:
    """
    Create Python language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for Python
    """
    return LanguageLiteralDescriptor(
        # Language syntax flags
        syntax=LanguageSyntaxFlags(
            single_line_comment="#",
            block_comment_open='"""',
            block_comment_close='"""',
            supports_raw_strings=True,  # r"..."
            supports_template_strings=False,  # No backticks
            supports_multiline_strings=True,  # """ """
            factory_wrappers=[],  # Python doesn't use factory methods
            supports_block_init=False,
            supports_ast_sequences=False,
        ),

        # String profiles (v2)
        string_profiles=[PYTHON_STRING_PROFILE],

        # Legacy patterns (to be migrated)
        _patterns=[
            # PYTHON_STRING removed - migrated to string_profiles
            PYTHON_LIST,
            PYTHON_TUPLE,
            PYTHON_DICT,
            PYTHON_SET,
        ]
    )

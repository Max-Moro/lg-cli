"""
Python language descriptor for literal optimization.

Defines patterns for Python literals: strings, lists, tuples, dicts, sets.
"""

from __future__ import annotations

import re

from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    SequenceProfile,
    MappingProfile,
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


# Python literal profiles

# String profile
PYTHON_STRING_PROFILE = StringProfile(
    query="(string) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[("", "{", "}")],
    interpolation_active=_is_f_string,
    preserve_whitespace=False,
    comment_name=None,
)

# Sequence profiles
PYTHON_LIST_PROFILE = SequenceProfile(
    query="(list) @lit",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    requires_ast_extraction=False,
)

PYTHON_TUPLE_PROFILE = SequenceProfile(
    query="(tuple) @lit",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="tuple",
    requires_ast_extraction=False,
)

PYTHON_SET_PROFILE = SequenceProfile(
    query="(set) @lit",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="set",
    requires_ast_extraction=False,
)

# Mapping profile
PYTHON_DICT_PROFILE = MappingProfile(
    query="(dictionary) @lit",
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…": "…"',
    min_elements=1,
    comment_name="object",
    preserve_all_keys=False,
)

def create_python_descriptor() -> LanguageLiteralDescriptor:
    """
    Create Python language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for Python
    """
    return LanguageLiteralDescriptor(
        # String profiles
        string_profiles=[PYTHON_STRING_PROFILE],

        # Sequence profiles
        sequence_profiles=[
            PYTHON_LIST_PROFILE,
            PYTHON_TUPLE_PROFILE,
            PYTHON_SET_PROFILE,
        ],

        # Mapping profiles
        mapping_profiles=[PYTHON_DICT_PROFILE],
    )

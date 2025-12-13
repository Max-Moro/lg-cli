"""
Python language descriptor for literal optimization.

Defines patterns for Python literals: strings, lists, tuples, dicts, sets.
"""

from __future__ import annotations

from ..optimizations.literals import *

PYTHON_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=["f", "F", "r", "R", "b", "B", "u", "U"],
    triple_quote_styles=['"""', "'''"],
    single_quote_styles=['"', "'"],
    default_delimiter='"',
)

_python_detector = DelimiterDetector(PYTHON_DELIMITER_CONFIG)


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
    opening=_python_detector.detect_opening,
    closing=_python_detector.detect_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[("", "{", "}")],
    interpolation_active=_is_f_string,
)

# Sequence profiles
PYTHON_LIST_PROFILE = SequenceProfile(
    query="(list) @lit",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    comment_name="array",
)

PYTHON_TUPLE_PROFILE = SequenceProfile(
    query="(tuple) @lit",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    comment_name="tuple",
)

PYTHON_SET_PROFILE = SequenceProfile(
    query="(set) @lit",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    comment_name="set",
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
    comment_name="object",
)

def create_python_descriptor() -> LanguageLiteralDescriptor:
    """
    Create Python language descriptor for literal optimization.

    Returns:
        Configured LanguageLiteralDescriptor for Python
    """
    return LanguageLiteralDescriptor(
        profiles=[
            PYTHON_STRING_PROFILE,
            PYTHON_LIST_PROFILE,
            PYTHON_TUPLE_PROFILE,
            PYTHON_SET_PROFILE,
            PYTHON_DICT_PROFILE,
        ]
    )

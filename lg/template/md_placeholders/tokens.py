"""
Tokens for parsing Markdown placeholders.

Extends existing placeholder context with MD-specific tokens.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_md_token_specs() -> List[TokenSpec]:
    """
    Returns token specifications for MD placeholders.

    These tokens will be added to existing 'placeholder' context.
    """
    return [
        # Hash # (for anchors md:path#anchor)
        TokenSpec(
            name="HASH",
            pattern=re.compile(r'#'),
        ),

        # Comma , (for parameters md:path,level:3)
        TokenSpec(
            name="COMMA",
            pattern=re.compile(r','),
        ),

        # Boolean values for parameters
        TokenSpec(
            name="BOOL_TRUE",
            pattern=re.compile(r'\btrue\b'),
            priority=60,  # Higher than default 50
        ),

        TokenSpec(
            name="BOOL_FALSE",
            pattern=re.compile(r'\bfalse\b'),
            priority=60,  # Higher than default 50
        ),

        # Numbers for parameters (e.g., level:3)
        TokenSpec(
            name="NUMBER",
            pattern=re.compile(r'\d+'),
        ),

        # Glob symbols (* and **)
        TokenSpec(
            name="GLOB_STAR",
            pattern=re.compile(r'\*+'),  # * or **
        ),
    ]


__all__ = ["get_md_token_specs"]

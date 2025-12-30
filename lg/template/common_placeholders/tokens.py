"""
Tokens for parsing section and template placeholders.

Defines tokens PLACEHOLDER_START (${), PLACEHOLDER_END (}),
and utility tokens for placeholder content.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_placeholder_token_specs() -> List[TokenSpec]:
    """
    Returns token specifications for placeholders.
    """
    return [
        # Placeholder start ${
        TokenSpec(
            name="PLACEHOLDER_START",
            pattern=re.compile(r'\$\{'),
        ),

        # Placeholder end }
        TokenSpec(
            name="PLACEHOLDER_END",
            pattern=re.compile(r'}'),
        ),

        # Colon : (for tpl:name, ctx:name)
        TokenSpec(
            name="COLON",
            pattern=re.compile(r':'),
        ),

        # At sign @ (for addressed references @origin:name)
        TokenSpec(
            name="AT",
            pattern=re.compile(r'@'),
        ),

        # Square brackets for addressing @[origin]:name
        TokenSpec(
            name="LBRACKET",
            pattern=re.compile(r'\['),
        ),

        TokenSpec(
            name="RBRACKET",
            pattern=re.compile(r']'),
        ),

        # Identifier (names of sections, templates, scopes)
        # Supports:
        # - Regular paths: agent/index, common/header
        # - Absolute paths: /agent/index
        # - Parent references: ../common, ../../shared/common
        # - Current dir references: ./local
        TokenSpec(
            name="IDENTIFIER",
            pattern=re.compile(r'(?:\.\.?/)+[a-zA-Z0-9_/.-]+|/?[a-zA-Z_][a-zA-Z0-9_/.-]*'),
        ),

        # Whitespace inside placeholders
        TokenSpec(
            name="WHITESPACE",
            pattern=re.compile(r'\s+'),
        ),
    ]


__all__ = ["get_placeholder_token_specs"]
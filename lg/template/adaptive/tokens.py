"""
Tokens for parsing adaptive constructs in templates.

Defines tokens for directives, conditions, modes, and comments.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_adaptive_token_specs() -> List[TokenSpec]:
    """
    Returns token specifications for adaptive constructs.
    """
    return [
        # Directive separators {% %}
        TokenSpec(
            name="DIRECTIVE_START",
            pattern=re.compile(r'\{%'),
        ),

        TokenSpec(
            name="DIRECTIVE_END",
            pattern=re.compile(r'%}'),
        ),

        # Comment separators {# #}
        TokenSpec(
            name="COMMENT_START",
            pattern=re.compile(r'\{#'),
        ),

        TokenSpec(
            name="COMMENT_END",
            pattern=re.compile(r'#}'),
        ),

        # Directive keywords (registered as identifiers)
        # Recognition happens during parsing

        # Logical operators AND, OR, NOT
        # (recognized as keywords during identifier parsing)

        # Parentheses for grouping in conditions
        TokenSpec(
            name="LPAREN",
            pattern=re.compile(r'\('),
        ),

        TokenSpec(
            name="RPAREN",
            pattern=re.compile(r'\)'),
        ),
    ]


__all__ = ["get_adaptive_token_specs"]


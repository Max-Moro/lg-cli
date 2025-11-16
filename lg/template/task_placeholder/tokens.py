"""
Tokens for parsing task placeholders.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_task_token_specs() -> List[TokenSpec]:
    """
    Returns token specifications for task placeholders.
    """
    return [
        # String literal in double quotes with escape sequences
        TokenSpec(
            name="STRING_LITERAL",
            pattern=re.compile(r'"(?:[^"\\]|\\.)*"'),
        ),
    ]


__all__ = ["get_task_token_specs"]
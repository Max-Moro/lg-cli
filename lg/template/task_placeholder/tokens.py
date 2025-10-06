"""
Токены для парсинга task-плейсхолдеров.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_task_token_specs() -> List[TokenSpec]:
    """
    Возвращает спецификации токенов для task-плейсхолдеров.
    """
    return [
        # Строковый литерал в двойных кавычках с escape-последовательностями
        TokenSpec(
            name="STRING_LITERAL",
            pattern=re.compile(r'"(?:[^"\\]|\\.)*"'),
        ),
    ]


__all__ = ["get_task_token_specs"]
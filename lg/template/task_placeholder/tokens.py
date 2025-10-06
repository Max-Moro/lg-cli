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
        # Ключевое слово task
        TokenSpec(
            name="TASK_KEYWORD",
            pattern=re.compile(r'\btask\b'),
        ),
        
        # Ключевое слово prompt
        TokenSpec(
            name="PROMPT_KEYWORD",
            pattern=re.compile(r'\bprompt\b'),
        ),
        
        # Строковый литерал в двойных кавычках с escape-последовательностями
        TokenSpec(
            name="STRING_LITERAL",
            pattern=re.compile(r'"(?:[^"\\]|\\.)*"'),
        ),
    ]


__all__ = ["get_task_token_specs"]
"""
Токены для парсинга Markdown-плейсхолдеров.

Расширяет существующий контекст плейсхолдеров специфичными для MD токенами.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_md_token_specs() -> List[TokenSpec]:
    """
    Возвращает спецификации токенов для MD-плейсхолдеров.
    
    Эти токены будут добавлены в существующий контекст 'placeholder'.
    """
    return [
        # Решётка # (для якорей md:path#anchor)
        TokenSpec(
            name="HASH",
            pattern=re.compile(r'#'),
        ),
        
        # Запятая , (для параметров md:path,level:3)
        TokenSpec(
            name="COMMA",
            pattern=re.compile(r','),
        ),
        
        # Булевы значения для параметров
        TokenSpec(
            name="BOOL_TRUE",
            pattern=re.compile(r'\btrue\b'),
            priority=60,  # Выше дефолтного 50
        ),
        
        TokenSpec(
            name="BOOL_FALSE",
            pattern=re.compile(r'\bfalse\b'),
            priority=60,  # Выше дефолтного 50
        ),
        
        # Числа для параметров (например, level:3)
        TokenSpec(
            name="NUMBER",
            pattern=re.compile(r'\d+'),
        ),
        
        # Глоб-символы (* и **)
        TokenSpec(
            name="GLOB_STAR",
            pattern=re.compile(r'\*+'),  # * или **
        ),
    ]


__all__ = ["get_md_token_specs"]

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
        # Префикс md для распознавания MD-плейсхолдеров
        TokenSpec(
            name="MD_PREFIX",
            pattern=re.compile(r'md\b'),  # \b обеспечивает границу слова
        ),
        
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
        ),
        
        TokenSpec(
            name="BOOL_FALSE",
            pattern=re.compile(r'\bfalse\b'),
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

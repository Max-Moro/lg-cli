"""
Токены для парсинга адаптивных конструкций в шаблонах.

Определяет токены для директив, условий, режимов и комментариев.
"""

from __future__ import annotations

import re
from typing import List

from ..types import TokenSpec


def get_adaptive_token_specs() -> List[TokenSpec]:
    """
    Возвращает спецификации токенов для адаптивных конструкций.
    """
    return [
        # Разделители директив {% %}
        TokenSpec(
            name="DIRECTIVE_START",
            pattern=re.compile(r'\{%'),
        ),
        
        TokenSpec(
            name="DIRECTIVE_END",
            pattern=re.compile(r'%}'),
        ),
        
        # Разделители комментариев {# #}
        TokenSpec(
            name="COMMENT_START",
            pattern=re.compile(r'\{#'),
        ),
        
        TokenSpec(
            name="COMMENT_END",
            pattern=re.compile(r'#}'),
        ),
        
        # Ключевые слова директив (регистрируются как идентификаторы)
        # Распознавание происходит при парсинге
        
        # Логические операторы AND, OR, NOT
        # (распознаются как ключевые слова при парсинге идентификаторов)
        
        # Скобки для группировки в условиях
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


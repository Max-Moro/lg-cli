"""
Токены для парсинга плейсхолдеров секций и шаблонов.

Определяет токены PLACEHOLDER_START (${), PLACEHOLDER_END (}), 
и служебные токены для содержимого плейсхолдеров.
"""

from __future__ import annotations

import re
from typing import List

from ..base import TokenSpec


def get_placeholder_token_specs() -> List[TokenSpec]:
    """
    Возвращает спецификации токенов для плейсхолдеров.
    """
    return [
        # Начало плейсхолдера ${
        TokenSpec(
            name="PLACEHOLDER_START",
            pattern=re.compile(r'\$\{'),
        ),
        
        # Конец плейсхолдера }
        TokenSpec(
            name="PLACEHOLDER_END", 
            pattern=re.compile(r'\}'),
        ),
        
        # Двоеточие : (для tpl:name, ctx:name)
        TokenSpec(
            name="COLON",
            pattern=re.compile(r':'),
        ),
        
        # Собачка @ (для адресных ссылок @origin:name)
        TokenSpec(
            name="AT",
            pattern=re.compile(r'@'),
        ),
        
        # Квадратные скобки для адресации @[origin]:name  
        TokenSpec(
            name="LBRACKET",
            pattern=re.compile(r'\['),
        ),
        
        TokenSpec(
            name="RBRACKET", 
            pattern=re.compile(r'\]'),
        ),
        
        # Идентификатор (имена секций, шаблонов, скоупов)
        # Разрешаем буквы, цифры, дефисы, подчеркивания, слеши, точки
        TokenSpec(
            name="IDENTIFIER",
            pattern=re.compile(r'[a-zA-Z_][a-zA-Z0-9_\-\/\.]*'),
        ),
        
        # Пробелы внутри плейсхолдеров
        TokenSpec(
            name="WHITESPACE",
            pattern=re.compile(r'\s+'),
        ),
    ]


__all__ = ["get_placeholder_token_specs"]
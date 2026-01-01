"""
Lexer for parsing conditional expressions.

Performs tokenization of a condition string, breaking it into meaningful elements:
- Keywords (tag, TAGSET, scope, AND, OR, NOT)
- Identifiers (names of tags, sets, and scopes)
- Symbols (parentheses, colons)
- Whitespace (ignored)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Iterator


@dataclass
class Token:
    """
    Token for condition parsing.

    Attributes:
        type: Token type (KEYWORD, IDENTIFIER, SYMBOL, EOF)
        value: Token value
        position: Position in the source string
    """
    type: str
    value: str
    position: int
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', pos={self.position})"


class ConditionLexer:
    """
    Lexer for splitting condition strings into tokens.

    Supported tokens:
    - KEYWORD: tag, TAGSET, scope, AND, OR, NOT
    - IDENTIFIER: names of tags, sets, scopes
    - SYMBOL: (, ), :
    - EOF: end of string
    """

    # Token specification: (regex_pattern, token_type, ignore_flag)
    TOKEN_SPECS = [
        # Whitespace and tabs (ignored)
        (r'\s+', 'WHITESPACE', True),

        # Symbols (checked before identifiers)
        (r'\(', 'SYMBOL', False),
        (r'\)', 'SYMBOL', False),
        (r':', 'SYMBOL', False),

        # Identifiers (Unicode letters, digits, underscores, hyphens)
        # Keywords will be determined after capture
        (r'[\w][\w-]*', 'IDENTIFIER', False),

        # Unknown symbol (error)
        (r'.', 'UNKNOWN', False),
    ]

    # Keywords for post-processing
    KEYWORDS = {
        'TAGSET', 'TAGONLY', 'scope', 'tag', 'task', 'AND', 'OR', 'NOT'
    }

    def __init__(self):
        # Compile regular expressions for better performance
        self._compiled_patterns = [
            (re.compile(pattern), token_type, ignore)
            for pattern, token_type, ignore in self.TOKEN_SPECS
        ]
    
    def tokenize(self, text: str) -> List[Token]:
        """
        Split a string into tokens.

        Args:
            text: Condition string to parse

        Returns:
            List of tokens, including EOF at the end

        Raises:
            ValueError: When an unknown character is detected
        """
        tokens: List[Token] = []
        position = 0

        while position < len(text):
            match_found = False

            for pattern, token_type, ignore in self._compiled_patterns:
                match = pattern.match(text, position)
                if match:
                    value = match.group(0)

                    if not ignore:
                        if token_type == 'UNKNOWN':
                            raise ValueError(f"Unexpected character '{value}' at position {position}")

                        # Determine token type: keyword or identifier
                        final_type = token_type
                        if token_type == 'IDENTIFIER' and value in self.KEYWORDS:
                            final_type = 'KEYWORD'

                        tokens.append(Token(
                            type=final_type,
                            value=value,
                            position=position
                        ))

                    position = match.end()
                    match_found = True
                    break

            if not match_found:
                # This should not happen since we have a pattern for any character
                raise ValueError(f"Failed to tokenize at position {position}")

        # Add EOF token
        tokens.append(Token(type='EOF', value='', position=position))

        return tokens
    
    def tokenize_stream(self, text: str) -> Iterator[Token]:
        """
        Generator for lazy tokenization.

        Args:
            text: Condition string to parse

        Yields:
            Token: Next token
        """
        for token in self.tokenize(text):
            yield token
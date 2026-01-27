"""
Lexical types.

Defines base token types.
Specific token types are registered by plugins.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from ..errors import LGUserError


class TokenType(enum.Enum):
    """Base token types in template. Plugins register their tokens via TokenRegistry."""
    TEXT = "TEXT"
    EOF = "EOF"


# Simplified token system - use strings directly
TokenTypeName = str


@dataclass(frozen=True)
class Token:
    """
    Token with position information for accurate error diagnostics.
    """
    type: TokenTypeName
    value: str
    position: int        # Position in source text
    line: int           # Line number (starting with 1)
    column: int         # Column number (starting with 1)

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, {self.line}:{self.column})"


class ParserError(LGUserError):
    """Syntax analysis error."""

    def __init__(self, message: str, token: Token):
        super().__init__(f"{message} at {token.line}:{token.column} (token: {token.type})")
        self.token = token
        self.line = token.line
        self.column = token.column


__all__ = [
    "TokenType", 
    "TokenTypeName",
    "Token", 
    "ParserError"
]
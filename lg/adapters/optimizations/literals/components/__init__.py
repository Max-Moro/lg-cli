"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .ast_sequence import ASTSequenceProcessor
from .block_init import BlockInitProcessor
from .placeholder import PlaceholderCommentFormatter

__all__ = ['ASTSequenceProcessor', 'BlockInitProcessor', 'PlaceholderCommentFormatter']

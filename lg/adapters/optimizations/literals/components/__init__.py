"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .interpolation import InterpolationHandler
from .ast_sequence import ASTSequenceProcessor
from .block_init import BlockInitProcessor
from .placeholder import PlaceholderCommentFormatter

__all__ = ['InterpolationHandler', 'ASTSequenceProcessor', 'BlockInitProcessor', 'PlaceholderCommentFormatter']

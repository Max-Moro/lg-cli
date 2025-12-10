"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .interpolation import InterpolationHandler
from .ast_sequence import ASTSequenceProcessor

__all__ = ['InterpolationHandler', 'ASTSequenceProcessor']

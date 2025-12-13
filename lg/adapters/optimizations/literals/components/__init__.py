"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .ast_sequence import ASTSequenceProcessor
from .block_init import BlockInitProcessorBase
from .string_literal import StringLiteralProcessor
from .standard_collections import StandardCollectionsProcessor

__all__ = [
    'ASTSequenceProcessor',
    'BlockInitProcessorBase',
    'StringLiteralProcessor',
    'StandardCollectionsProcessor',
]

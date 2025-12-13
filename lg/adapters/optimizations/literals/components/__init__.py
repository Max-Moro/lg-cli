"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .base import LiteralProcessor
from .ast_sequence import ASTSequenceProcessor
from .block_init import BlockInitProcessorBase
from .java_double_brace import JavaDoubleBraceProcessor
from .rust_let_group import RustLetGroupProcessor
from .string_literal import StringLiteralProcessor
from .standard_collections import StandardCollectionsProcessor
from .cpp_initializer_list import CppInitializerListProcessor

__all__ = [
    'LiteralProcessor',
    'ASTSequenceProcessor',
    'BlockInitProcessorBase',
    'JavaDoubleBraceProcessor',
    'RustLetGroupProcessor',
    'StringLiteralProcessor',
    'StandardCollectionsProcessor',
    'CppInitializerListProcessor',
]

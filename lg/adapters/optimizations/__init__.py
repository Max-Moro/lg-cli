"""
Optimization modules for language adapters.
Each module handles a specific type of code optimization.
"""

from .public_api import PublicApiOptimizer
from .function_bodies import FunctionBodyOptimizer
from .comments import CommentOptimizer, CommentAnalyzer
from .imports import ImportOptimizer, TreeSitterImportAnalyzer, ImportClassifier, ImportInfo
from .literals import LiteralPipeline
from .literals.descriptor import LanguageLiteralDescriptor

__all__ = [
    "PublicApiOptimizer",
    "FunctionBodyOptimizer",
    "CommentOptimizer",
    "ImportOptimizer",
    "ImportInfo",
    "LiteralPipeline",
    "LanguageLiteralDescriptor",
    "TreeSitterImportAnalyzer",
    "ImportClassifier",
    "CommentAnalyzer",
]

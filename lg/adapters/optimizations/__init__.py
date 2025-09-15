"""
Optimization modules for language adapters.
Each module handles a specific type of code optimization.
"""

from .public_api import PublicApiOptimizer
from .function_bodies import FunctionBodyOptimizer  
from .comments import CommentOptimizer
from .imports import ImportOptimizer, TreeSitterImportAnalyzer, ImportClassifier
from .literals import LiteralOptimizer

__all__ = [
    "PublicApiOptimizer",
    "FunctionBodyOptimizer", 
    "CommentOptimizer",
    "ImportOptimizer",
    "LiteralOptimizer",
    "TreeSitterImportAnalyzer",
    "ImportClassifier",
]

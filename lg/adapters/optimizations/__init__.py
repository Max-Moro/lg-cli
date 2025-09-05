"""
Optimization modules for language adapters.
Each module handles a specific type of code optimization.
"""

from .public_api import PublicApiOptimizer
from .function_bodies import FunctionBodyOptimizer  
from .comments import CommentOptimizer
from .imports import ImportOptimizer, ImportAnalyzer, ImportClassifier
from .literals import LiteralOptimizer
from .fields import FieldOptimizer, FieldsClassifier

__all__ = [
    "PublicApiOptimizer",
    "FunctionBodyOptimizer", 
    "CommentOptimizer",
    "ImportOptimizer",
    "LiteralOptimizer",
    "FieldOptimizer",
    "FieldsClassifier",
    "ImportAnalyzer",
    "ImportClassifier",
]

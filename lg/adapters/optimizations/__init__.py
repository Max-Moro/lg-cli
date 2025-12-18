"""
Optimization modules for language adapters.
Each module handles a specific type of code optimization.
"""

from .public_api import PublicApiOptimizer
from .function_bodies import FunctionBodyOptimizer
from .comments import CommentOptimizer
from .imports import ImportOptimizer, TreeSitterImportAnalyzer, ImportClassifier
from .literals import LiteralPipeline
from .literals.descriptor import LanguageLiteralDescriptor
from .comment_analysis import CommentAnalyzer
from .text_utils import (
    extract_sentence,
    clean_multiline_comment_content,
    get_line_range,
    detect_base_indent,
)
from ..comment_style import CommentStyle

__all__ = [
    "PublicApiOptimizer",
    "FunctionBodyOptimizer",
    "CommentOptimizer",
    "ImportOptimizer",
    "LiteralPipeline",
    "LanguageLiteralDescriptor",
    "TreeSitterImportAnalyzer",
    "ImportClassifier",
    "CommentAnalyzer",
    "extract_sentence",
    "clean_multiline_comment_content",
    "get_line_range",
    "detect_base_indent",
]

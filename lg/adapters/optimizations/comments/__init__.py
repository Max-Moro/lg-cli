"""
Comment Optimization.

This package provides comprehensive comment and docstring processing
capabilities across multiple programming languages.
"""

from .optimizer import CommentOptimizer
from .analyzer import CommentAnalyzer, TruncationStyle
from .text_utils import (
    extract_sentence,
    clean_multiline_comment_content,
    get_line_range,
    detect_base_indent,
)

__all__ = [
    "CommentOptimizer",
    "CommentAnalyzer",
    "TruncationStyle",
    "extract_sentence",
    "clean_multiline_comment_content",
    "get_line_range",
    "detect_base_indent",
]

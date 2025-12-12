"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .element_parser import ElementParser, Element, ParseConfig
from .interpolation import InterpolationHandler
from .indentation import detect_base_indent, detect_element_indent
from .comment_formatter import CommentFormatter

__all__ = ['ElementParser', 'Element', 'ParseConfig', 'InterpolationHandler', 'detect_base_indent', 'detect_element_indent', 'CommentFormatter']

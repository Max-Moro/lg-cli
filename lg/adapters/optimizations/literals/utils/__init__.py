"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .delimiter_detection import DelimiterConfig, DelimiterDetector
from .element_parser import ElementParser, Element, ParseConfig
from .indentation import detect_base_indent, detect_element_indent
from .interpolation import InterpolationHandler

__all__ = [
    'ElementParser',
    'Element',
    'ParseConfig',
    'InterpolationHandler',
    'detect_base_indent',
    'detect_element_indent',
    'DelimiterConfig',
    'DelimiterDetector',
]

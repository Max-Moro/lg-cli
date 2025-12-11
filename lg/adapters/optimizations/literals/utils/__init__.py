"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .element_parser import ElementParser, Element, ParseConfig
from .budgeting import BudgetCalculator
from .interpolation import InterpolationHandler
from .indentation import detect_base_indent, detect_element_indent

__all__ = ['ElementParser', 'Element', 'ParseConfig', 'BudgetCalculator', 'InterpolationHandler', 'detect_base_indent', 'detect_element_indent']

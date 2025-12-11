"""
Components for literals optimization.

Reusable, self-contained components for handling specific aspects
of literal string processing.
"""

from .element_parser import ElementParser, Element, ParseConfig
from .budgeting import BudgetCalculator
from .interpolation import InterpolationHandler

__all__ = ['ElementParser', 'Element', 'ParseConfig', 'BudgetCalculator', 'InterpolationHandler']

"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .categories import (
    LiteralCategory,
    PlaceholderPosition,
    LiteralPattern,
    ParsedLiteral,
    TrimResult,
)
from .patterns import StringProfile, SequenceProfile, MappingProfile, LanguageSyntaxFlags
from .core import LiteralOptimizer
from .descriptor import LanguageLiteralDescriptor
from .formatter import ResultFormatter, FormattedResult
from .handler import LanguageLiteralHandler
from .parser import ElementParser, ParseConfig, Element
from .selector import BudgetSelector, SelectionBase, Selection

__all__ = [
    # Descriptor types
    "LanguageLiteralDescriptor",
    "LiteralCategory",
    "PlaceholderPosition",
    "LiteralPattern",

    # Profile types
    "StringProfile",
    "SequenceProfile",
    "MappingProfile",
    "LanguageSyntaxFlags",

    # Main optimizer
    "LiteralOptimizer"
]

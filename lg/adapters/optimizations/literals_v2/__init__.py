"""
Literal Optimization v2 - New architecture for literal trimming.

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
from .parser import ElementParser, ParseConfig, Element
from .selector import BudgetSelector, Selection
from .formatter import ResultFormatter, FormattedResult
from .descriptor import LanguageLiteralDescriptor
from .handler import LanguageLiteralHandler
from .core import LiteralOptimizerV2, create_optimizer

__all__ = [
    # Categories and types
    "LiteralCategory",
    "PlaceholderPosition",
    "LiteralPattern",
    "ParsedLiteral",
    "TrimResult",
    # Parser
    "ElementParser",
    "ParseConfig",
    "Element",
    # Selector
    "BudgetSelector",
    "Selection",
    # Formatter
    "ResultFormatter",
    "FormattedResult",
    # Descriptor and handler
    "LanguageLiteralDescriptor",
    "LanguageLiteralHandler",
    # Main optimizer
    "LiteralOptimizerV2",
    "create_optimizer",
]

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
from .descriptor import LanguageLiteralDescriptor
from .element_parser import ElementParser, ParseConfig, Element
from .handler import LanguageLiteralHandler
from .patterns import (
    StringProfile,
    SequenceProfile,
    MappingProfile,
    FactoryProfile,
    BlockInitProfile,
    LanguageSyntaxFlags,
    LiteralProfile,
)
from .processing import LiteralPipeline
from .processing.formatter import ResultFormatter, FormattedResult
from .processing.selector import BudgetSelector, SelectionBase, Selection

__all__ = [
    # Descriptor types
    "LanguageLiteralDescriptor",
    "LiteralCategory",
    "PlaceholderPosition",
    "LiteralPattern",
    "ParsedLiteral",
    "TrimResult",

    # Profile types
    "StringProfile",
    "SequenceProfile",
    "MappingProfile",
    "FactoryProfile",
    "BlockInitProfile",
    "LanguageSyntaxFlags",
    "LiteralProfile",

    # Main optimizer
    "LiteralPipeline",
    "LanguageLiteralHandler",
    "ResultFormatter",
    "FormattedResult",
    "ElementParser",
    "ParseConfig",
    "Element",
    "BudgetSelector",
    "Selection",
]

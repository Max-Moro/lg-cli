"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .categories import (
    ParsedLiteral,
    TrimResult,
)
from .descriptor import LanguageLiteralDescriptor
from .element_parser import ElementParser, ParseConfig, Element
from .handler import LanguageLiteralHandler
from .patterns import (
    LiteralCategory,
    PlaceholderPosition,
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
    # Enums and types
    "LiteralCategory",
    "PlaceholderPosition",
    "ParsedLiteral",
    "TrimResult",

    # Descriptor
    "LanguageLiteralDescriptor",

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

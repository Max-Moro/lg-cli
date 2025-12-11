"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .descriptor import LanguageLiteralDescriptor
from .utils.element_parser import ElementParser, ParseConfig, Element
from .patterns import (
    PlaceholderPosition,
    ParsedLiteral,
    TrimResult,
    StringProfile,
    CollectionProfile,
    SequenceProfile,
    MappingProfile,
    FactoryProfile,
    BlockInitProfile,
    LanguageSyntaxFlags,
    LiteralProfile,
)
from .processing import LiteralPipeline
from .processing.formatter import ResultFormatter, FormattedResult
from .processing.selector import BudgetSelector, Selection

__all__ = [
    # Descriptor and types
    "LanguageLiteralDescriptor",
    "LanguageSyntaxFlags",
    "PlaceholderPosition",

    # Profiles
    "StringProfile",
    "SequenceProfile",
    "MappingProfile",
    "FactoryProfile",
    "BlockInitProfile",

    # Main optimizer
    "LiteralPipeline",
]

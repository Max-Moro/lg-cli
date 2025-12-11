"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .descriptor import LanguageLiteralDescriptor
from .patterns import (
    LanguageSyntaxFlags, PlaceholderPosition, StringProfile,
    SequenceProfile, MappingProfile, FactoryProfile, BlockInitProfile
)
from .processing import LiteralPipeline

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

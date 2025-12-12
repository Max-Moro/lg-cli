"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .descriptor import LanguageLiteralDescriptor
from .patterns import (
    PlaceholderPosition, StringProfile,
    SequenceProfile, MappingProfile, FactoryProfile, BlockInitProfile
)
from .processing import LiteralPipeline
from .utils import DelimiterConfig, DelimiterDetector

__all__ = [
    # Descriptor and types
    "LanguageLiteralDescriptor",
    "PlaceholderPosition",

    # Profiles
    "StringProfile",
    "SequenceProfile",
    "MappingProfile",
    "FactoryProfile",
    "BlockInitProfile",

    # Main optimizer
    "LiteralPipeline",

    # Utils
    "DelimiterConfig",
    "DelimiterDetector",
]

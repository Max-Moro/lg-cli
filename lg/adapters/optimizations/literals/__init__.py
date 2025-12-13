"""
Literal Optimization.

This package provides a unified, extensible system for optimizing
literal data in source code across multiple programming languages.
"""

from .descriptor import LanguageLiteralDescriptor
from .patterns import (
    PlaceholderPosition, StringProfile,
    SequenceProfile, MappingProfile, FactoryProfile, BlockInitProfile,
    TrimResult, LiteralProfile
)
from .processing import LiteralPipeline
from .utils import DelimiterConfig, DelimiterDetector
from .processor import LiteralProcessor
from .components.block_init import BlockInitProcessorBase
from .components.standard_collections import StandardCollectionsProcessor

__all__ = [
    # Descriptor and types
    "LanguageLiteralDescriptor",
    "PlaceholderPosition",
    "LiteralProfile",
    "TrimResult",

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

    # Base classes for custom components
    "LiteralProcessor",
    "BlockInitProcessorBase",
    "StandardCollectionsProcessor",
]

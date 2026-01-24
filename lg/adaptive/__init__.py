"""
Adaptive modes and tags system.

Provides data models and utilities for the new adaptive system
with context-dependent mode-sets and tag-sets.
"""

from __future__ import annotations

from .model import (
    RunsMap,
    VcsMode,
    Mode,
    ModeSet,
    Tag,
    TagSet,
    AdaptiveModel,
)

from .errors import (
    AdaptiveError,
    ExtendsCycleError,
    MetaSectionRenderError,
    MultipleIntegrationModeSetsError,
    NoIntegrationModeSetError,
    ProviderNotSupportedError,
    InvalidModeReferenceError,
    SectionNotFoundInExtendsError,
)

from .section_extractor import extract_adaptive_model

from .validation import (
    AdaptiveValidator,
    validate_model,
    validate_mode_reference,
    validate_provider_support,
)

from .extends_resolver import ExtendsResolver, ResolvedSectionData

from .context_collector import ContextCollector, CollectedSections

from .context_resolver import ContextResolver, ContextAdaptiveData

__all__ = [
    # Model
    "RunsMap",
    "VcsMode",
    "Mode",
    "ModeSet",
    "Tag",
    "TagSet",
    "AdaptiveModel",
    # Errors
    "AdaptiveError",
    "ExtendsCycleError",
    "MetaSectionRenderError",
    "MultipleIntegrationModeSetsError",
    "NoIntegrationModeSetError",
    "ProviderNotSupportedError",
    "InvalidModeReferenceError",
    "SectionNotFoundInExtendsError",
    # Section extractor
    "extract_adaptive_model",
    # Validation
    "AdaptiveValidator",
    "validate_model",
    "validate_mode_reference",
    "validate_provider_support",
    # Extends resolver
    "ExtendsResolver",
    "ResolvedSectionData",
    # Context collector
    "ContextCollector",
    "CollectedSections",
    # Context resolver
    "ContextResolver",
    "ContextAdaptiveData",
]

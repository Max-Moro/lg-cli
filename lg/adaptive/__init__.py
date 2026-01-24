"""
Adaptive capabilities system for Listing Generator.

Provides mode-sets, tag-sets, and context-dependent configuration resolution.
"""

from __future__ import annotations

from .model import (
    Mode,
    ModeSet,
    Tag,
    TagSet,
    AdaptiveModel,
    ModeOptions,
    RunsMap,
    VcsMode,
)
from .context_resolver import ContextResolver, ContextAdaptiveData
from .extends_resolver import ExtendsResolver, ResolvedSectionData
from .section_extractor import extract_adaptive_model
from .validation import (
    AdaptiveValidator,
    validate_model,
    validate_mode_reference,
    validate_provider_support,
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
from .listing import list_mode_sets, list_tag_sets

__all__ = [
    # Model
    "Mode",
    "ModeSet",
    "Tag",
    "TagSet",
    "AdaptiveModel",
    "ModeOptions",
    "RunsMap",
    "VcsMode",
    # Resolvers
    "ContextResolver",
    "ContextAdaptiveData",
    "ExtendsResolver",
    "ResolvedSectionData",
    # Utilities
    "extract_adaptive_model",
    # Validation
    "AdaptiveValidator",
    "validate_model",
    "validate_mode_reference",
    "validate_provider_support",
    # Errors
    "AdaptiveError",
    "ExtendsCycleError",
    "MetaSectionRenderError",
    "MultipleIntegrationModeSetsError",
    "NoIntegrationModeSetError",
    "ProviderNotSupportedError",
    "InvalidModeReferenceError",
    "SectionNotFoundInExtendsError",
    # Listing
    "list_mode_sets",
    "list_tag_sets",
]

"""
Adaptive modes and tags system.

Provides context-specific mode-sets and tag-sets with:
- Section inheritance via `extends`
- Integration mode-sets with `runs` for AI providers
- Content mode-sets for adaptive template content
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

__all__ = [
    # Model types
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
]

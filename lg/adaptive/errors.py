"""
Specialized exceptions for the adaptive system.

Provides informative error messages for extends resolution,
validation failures, and runtime errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


class AdaptiveError(Exception):
    """Base class for adaptive system errors."""
    pass


@dataclass
class ExtendsCycleError(AdaptiveError):
    """Circular dependency in extends chain."""
    cycle: List[str]

    def __str__(self) -> str:
        return f"Circular extends dependency: {' -> '.join(self.cycle)}"


@dataclass
class MetaSectionRenderError(AdaptiveError):
    """Attempt to render meta-section (no filters)."""
    section_name: str

    def __str__(self) -> str:
        return f"Cannot render meta-section '{self.section_name}' (has no filters)"


@dataclass
class MultipleIntegrationModeSetsError(AdaptiveError):
    """Multiple integration mode-sets found in context."""
    mode_sets: List[str]
    context_name: str = ""

    def __str__(self) -> str:
        ctx_info = f" in context '{self.context_name}'" if self.context_name else ""
        return (
            f"Multiple integration mode-sets found{ctx_info}: {', '.join(self.mode_sets)}. "
            f"Only one integration mode-set is allowed per context."
        )


@dataclass
class NoIntegrationModeSetError(AdaptiveError):
    """No integration mode-set found in context."""
    context_name: str = ""

    def __str__(self) -> str:
        ctx_info = f" in context '{self.context_name}'" if self.context_name else ""
        return f"No integration mode-set found{ctx_info}. At least one mode-set with 'runs' is required."


@dataclass
class ProviderNotSupportedError(AdaptiveError):
    """Provider not supported by context's integration mode-set."""
    provider_id: str
    context_name: str
    available_providers: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        msg = f"Provider '{self.provider_id}' is not supported by context '{self.context_name}'"
        if self.available_providers:
            msg += f". Available providers: {', '.join(self.available_providers)}"
        return msg


@dataclass
class InvalidModeReferenceError(AdaptiveError):
    """Invalid {% mode %} reference - mode not found in context."""
    modeset: str
    mode: str
    context_name: str = ""
    available_modes: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        ctx_info = f" in context '{self.context_name}'" if self.context_name else ""
        msg = f"Mode '{self.modeset}:{self.mode}' not found{ctx_info}"
        if self.available_modes:
            msg += f". Available modes in '{self.modeset}': {', '.join(self.available_modes)}"
        return msg


@dataclass
class UnknownModeSetError(AdaptiveError):
    """Unknown mode-set in --mode argument."""
    modeset_id: str
    available_sets: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        avail = f". Available: {', '.join(self.available_sets)}" if self.available_sets else ""
        return f"Unknown mode set '{self.modeset_id}'{avail}"


@dataclass
class SectionNotFoundInExtendsError(AdaptiveError):
    """Section referenced in extends not found."""
    section_name: str
    parent_section: str

    def __str__(self) -> str:
        return f"Section '{self.section_name}' referenced in extends of '{self.parent_section}' not found"


__all__ = [
    "AdaptiveError",
    "ExtendsCycleError",
    "MetaSectionRenderError",
    "MultipleIntegrationModeSetsError",
    "NoIntegrationModeSetError",
    "ProviderNotSupportedError",
    "InvalidModeReferenceError",
    "UnknownModeSetError",
    "SectionNotFoundInExtendsError",
]

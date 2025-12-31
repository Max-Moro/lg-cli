from __future__ import annotations

from .model import (
    SectionCfg,
    AdapterConfig,
    ConditionalAdapterOptions,
    TargetRule,
    EmptyPolicy,
)
from .service import SectionService, SectionLocation, ScopeIndex, list_sections, list_sections_peek

__all__ = [
    # Model
    "SectionCfg",
    "AdapterConfig",
    "ConditionalAdapterOptions",
    "TargetRule",
    "EmptyPolicy",
    # Service
    "SectionService",
    "SectionLocation",
    "ScopeIndex",
    "list_sections",
    "list_sections_peek",
]

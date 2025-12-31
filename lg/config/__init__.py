"""
Configuration loading for Listing Generator.
"""

from __future__ import annotations

from .adaptive_loader import process_adaptive_options
from .model import Config
from .load import load_config

# Re-export from lg/section for backward compatibility
from ..section import (
    SectionCfg,
    AdapterConfig,
    ConditionalAdapterOptions,
    TargetRule,
    EmptyPolicy,
    list_sections,
    list_sections_peek,
)

__all__ = [
    "Config",
    "load_config",
    "process_adaptive_options",
    # Re-exports from lg/section
    "SectionCfg",
    "AdapterConfig",
    "ConditionalAdapterOptions",
    "TargetRule",
    "EmptyPolicy",
    "list_sections",
    "list_sections_peek",
]
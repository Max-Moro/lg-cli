"""
Resource configurations for the addressing system.

Contains configurations that are shared across subsystems
to avoid circular imports.
"""

from __future__ import annotations

from .types import ResourceConfig

# Section reference: resolved via SectionService
SECTION_CONFIG = ResourceConfig(
    kind="sec",
    is_section=True,
)


__all__ = ["SECTION_CONFIG"]

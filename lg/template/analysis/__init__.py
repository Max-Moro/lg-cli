"""
Template analysis utilities.

This package contains utilities for analyzing template structure
without performing full rendering. Used for collecting sections,
building dependency graphs, and other static analysis tasks.
"""

from __future__ import annotations

from .section_collector import SectionCollector, CollectedSections

__all__ = ["SectionCollector", "CollectedSections"]

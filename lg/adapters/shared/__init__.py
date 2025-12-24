"""
Shared infrastructure for code optimizations.

This package provides unified components for:
- Public API optimization (filtering private elements)
- Function body optimization (stripping/trimming bodies)

Components:
- ElementProfile: Declarative description of element types
- CodeElement: Unified representation of code elements
- LanguageCodeDescriptor: Language-specific profiles collection
- ElementCollector: Universal element collector
"""

from .profiles import ElementProfile
from .models import CodeElement
from .descriptor import LanguageCodeDescriptor
from .collector import ElementCollector
from .utils import is_inside_container, compute_element_range_with_trailing

__all__ = [
    "ElementProfile",
    "CodeElement",
    "LanguageCodeDescriptor",
    "ElementCollector",
    "is_inside_container",
    "compute_element_range_with_trailing",
]

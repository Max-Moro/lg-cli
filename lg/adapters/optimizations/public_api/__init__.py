"""
Profile-based public API optimization.
Infrastructure for declarative element collection and filtering.
"""

from .optimizer import PublicApiOptimizer
from .profiles import LanguageElementProfiles

__all__ = [
    "PublicApiOptimizer",
    "LanguageElementProfiles"
]

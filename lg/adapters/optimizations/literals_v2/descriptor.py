"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .categories import LiteralPattern


@dataclass
class LanguageLiteralDescriptor:
    """
    Declarative description of literal patterns in a language.

    Languages provide this descriptor to define how their literals
    should be recognized and processed.
    """

    # List of literal patterns in priority order
    patterns: List[LiteralPattern]

    def get_pattern_for(self, tree_sitter_type: str) -> LiteralPattern:
        """
        Get the first matching pattern for a tree-sitter node type.

        Args:
            tree_sitter_type: The tree-sitter node type

        Returns:
            Matching LiteralPattern or None
        """
        for pattern in self.patterns:
            if tree_sitter_type in pattern.tree_sitter_types:
                return pattern
        return None

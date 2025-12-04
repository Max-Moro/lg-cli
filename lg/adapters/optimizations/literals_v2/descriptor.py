"""
Language literal descriptors.

Declarative definitions of literal patterns and behavior for each language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

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

    def get_pattern_for(
        self,
        tree_sitter_type: str,
        wrapper: Optional[str] = None
    ) -> Optional[LiteralPattern]:
        """
        Get the first matching pattern for a tree-sitter node type.

        Patterns are checked in order (respecting priority). A pattern matches if:
        1. tree_sitter_type is in pattern.tree_sitter_types
        2. If pattern.wrapper_match is set, wrapper must match the regex

        Args:
            tree_sitter_type: The tree-sitter node type
            wrapper: Optional wrapper text (e.g., "List.of", "Map.ofEntries")

        Returns:
            Matching LiteralPattern or None
        """
        # Sort by priority (higher first)
        sorted_patterns = sorted(
            self.patterns,
            key=lambda p: p.priority,
            reverse=True
        )

        for pattern in sorted_patterns:
            if tree_sitter_type not in pattern.tree_sitter_types:
                continue

            # Check wrapper_match if specified
            if pattern.wrapper_match is not None:
                if wrapper is None:
                    continue
                if not re.match(pattern.wrapper_match, wrapper):
                    continue

            return pattern

        return None

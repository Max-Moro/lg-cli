"""
Centralized placeholder management system for language adapters.
Provides unified API and intelligent placeholder collapsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Any

from .comment_style import CommentStyle
from .tree_sitter_support import Node


class PlaceholderAction(Enum):
    """Action type for placeholder - determines text suffix."""
    OMIT = "omitted"       # Complete removal of element
    TRUNCATE = "truncated"  # Partial reduction/trimming


# Pluralization rules for element types
_PLURAL_FORMS: Dict[str, str] = {
    "class": "classes",
    "property": "properties",
    "body": "bodies",
}


def _pluralize(word: str, count: int) -> str:
    """Pluralize word based on count."""
    if count == 1:
        return word
    # Check special forms
    if word in _PLURAL_FORMS:
        return _PLURAL_FORMS[word]
    # Default: add 's'
    return word + "s"


@dataclass
class PlaceholderSpec:
    """
    Placeholder specification with metadata.
    Stores structured placeholder information without binding to a specific format.
    """
    # Position in file (required)
    start_char: int
    end_char: int

    # Element type: "function", "method", "import", "comment", "literal", etc.
    # For bodies use: "function_body", "method_body", "getter_body", etc.
    element_type: str

    # Action: OMIT (complete removal) or TRUNCATE (partial reduction)
    action: PlaceholderAction = PlaceholderAction.OMIT

    # Placeholder indentation prefix
    placeholder_prefix: str = ""

    # Number of elements (for imports, comments that can be merged)
    count: int = 1

    # Lines removed - only meaningful for body types, explicitly passed by optimizer
    lines_removed: int = 0
    
    @property
    def width(self) -> int:
        """Width of placeholder in characters."""
        return self.end_char - self.start_char

    def overlaps(self, other: PlaceholderSpec) -> bool:
        """Check if this placeholder overlaps with another."""
        return not (self.end_char <= other.start_char or other.end_char <= self.start_char)

    @property
    def position_key(self) -> Tuple[int, int]:
        """Key for sorting by position."""
        return self.start_char, self.end_char

    def can_merge_with(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Check if this placeholder can be merged with another.

        Merge conditions:
        - Same element type and action
        - Suitable types (not bodies)
        - No significant content between placeholders
        """
        if self.element_type != other.element_type:
            return False

        if self.action != other.action:
            return False

        # Cannot collapse body placeholders - they represent distinct function/method bodies
        if self.element_type.endswith("_body"):
            return False

        # Check content between placeholders
        return not self._has_significant_content_between(other, source_text)

    def _has_significant_content_between(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Conservative check for significant content between placeholders.

        Uses strict approach: placeholders are merged only if there is truly no code between them -
        only empty lines, spaces and tabs. Also checks that placeholders have the same number
        of characters from the line start.

        Args:
            other: Another placeholder for comparison
            source_text: Source text of document

        Returns:
            True if there is any code between placeholders or different indentation, False if only whitespace and same indentation
        """

        # Determine range between placeholders
        if self.end_char <= other.start_char:
            # self goes before other
            start_char = self.end_char
            end_char = other.start_char
        elif other.end_char <= self.start_char:
            # other goes before self
            start_char = other.end_char
            end_char = self.start_char
        else:
            # Placeholders overlap - can merge
            return False

        # Get content between placeholders
        if start_char >= end_char:
            return False

        try:
            content_between = source_text[start_char:end_char]
        except (UnicodeDecodeError, IndexError):
            # On decoding errors, conservatively block merge
            return True

        # Conservative approach: any non-empty content blocks merge
        stripped = content_between.strip()
        if stripped:
            return True

        # Check number of characters from line start for each placeholder
        self_chars_from_line_start = self._count_chars_from_line_start(self.start_char, source_text)
        other_chars_from_line_start = self._count_chars_from_line_start(other.start_char, source_text)

        if self_chars_from_line_start != other_chars_from_line_start:
            return True

        return False

    def _count_chars_from_line_start(self, char_position: int, source_text: str) -> int:
        """
        Count number of characters from line start to given character position.

        Args:
            char_position: Character position in text
            source_text: Source text of document

        Returns:
            Number of characters from nearest '\n' on the left to position
        """
        # Go left from position and search for nearest '\n'
        for i in range(char_position - 1, -1, -1):
            if i < len(source_text) and source_text[i] == '\n':
                # Found '\n', count characters from it to position
                return char_position - i - 1

        # If '\n' not found, we're at the beginning of file
        return char_position
    
    def merge_with(self, other: PlaceholderSpec, source_text: str) -> PlaceholderSpec:
        """Create merged placeholder."""
        if not self.can_merge_with(other, source_text):
            raise ValueError("Cannot merge incompatible placeholders")

        # Merged boundaries
        start_char = min(self.start_char, other.start_char)
        end_char = max(self.end_char, other.end_char)

        return PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=self.element_type,
            action=self.action,
            placeholder_prefix=self.placeholder_prefix,
            count=self.count + other.count,
            lines_removed=self.lines_removed + other.lines_removed,
        )


class PlaceholderManager:
    """
    Central manager for placeholder management.
    Provides unified API and handles collapsing.
    """

    def __init__(self, raw_text: str, comment_style: CommentStyle, placeholder_style: str):
        self.raw_text = raw_text
        self.comment_style = comment_style
        self.placeholder_style = placeholder_style
        self.placeholders: List[PlaceholderSpec] = []

    # ============= Public API for adding placeholders =============

    def add_placeholder(
        self,
        element_type: str,
        start_char: int,
        end_char: int,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        placeholder_prefix: str = "",
        count: int = 1,
        lines_removed: int = 0,
    ) -> None:
        """
        Add placeholder with explicit coordinates.

        Args:
            element_type: Type of element ("function_body", "import", "comment", etc.)
            start_char: Start position in characters
            end_char: End position in characters
            action: OMIT for complete removal, TRUNCATE for partial reduction
            placeholder_prefix: Indentation prefix for placeholder text
            count: Number of elements (for merging similar placeholders)
            lines_removed: Explicit line count (only for body types)
        """
        spec = PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=element_type,
            action=action,
            placeholder_prefix=placeholder_prefix,
            count=count,
            lines_removed=lines_removed,
        )
        self._add_placeholder_with_priority(spec)

    def add_placeholder_for_node(
        self,
        element_type: str,
        node: Node,
        doc,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        count: int = 1,
    ) -> None:
        """
        Add placeholder for Tree-sitter node.

        Args:
            element_type: Type of element
            node: Tree-sitter node to replace
            doc: TreeSitterDocument for coordinate conversion
            action: OMIT or TRUNCATE
            count: Number of elements
        """
        start_char, end_char = doc.get_node_range(node)
        spec = PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=element_type,
            action=action,
            count=count,
        )
        self._add_placeholder_with_priority(spec)

    # ============= Internal methods =============

    def _add_placeholder_with_priority(self, spec: PlaceholderSpec) -> None:
        """
        Add placeholder applying priority policy for wider edits.

        Args:
            spec: Placeholder specification to add
        """
        # New policy: wider placeholders always win
        new_width = spec.width

        # Check all existing placeholders
        placeholders_to_remove = []
        for i, existing in enumerate(self.placeholders):
            if spec.overlaps(existing):
                existing_width = existing.width

                if new_width > existing_width:
                    # New placeholder is wider - remove existing one
                    placeholders_to_remove.append(i)
                elif new_width < existing_width:
                    # New placeholder is narrower - skip it
                    return
                else:
                    # Same width - first wins (skip new one)
                    return

        # Remove absorbed placeholders (in reverse order to avoid index shift)
        for i in reversed(placeholders_to_remove):
            del self.placeholders[i]

        self.placeholders.append(spec)

    def _generate_placeholder_text(self, spec: PlaceholderSpec) -> str:
        """Generate placeholder text based on type and style."""
        content = self._get_placeholder_content(spec)

        # For docstrings always use native language wrapping
        if spec.element_type == "docstring":
            doc_start, doc_end = self.comment_style.doc_markers
            if doc_end:
                return f"{spec.placeholder_prefix}{doc_start} {content} {doc_end}"
            else:
                # Single-line docstring style (e.g., /// for Rust, // for Go)
                return f"{spec.placeholder_prefix}{doc_start} {content}\n"

        # Standard logic for regular comments
        if self.placeholder_style == "inline":
            return f"{spec.placeholder_prefix}{self.comment_style.single_line} {content}"
        else:  # self.placeholder_style == "block"
            block_start, block_end = self.comment_style.multi_line
            return f"{spec.placeholder_prefix}{block_start} {content} {block_end}"

    def _get_placeholder_content(self, spec: PlaceholderSpec) -> str:
        """
        Generate placeholder content based on element type and action.

        Universal algorithm:
        1. Start with ellipsis "…"
        2. Add count if > 1 (except for comments/docstrings - they represent semantic units)
        3. Add element type (pluralized if count > 1)
        4. Add action word (omitted/truncated)
        5. Add lines suffix for body types with lines_removed > 1
        """
        parts = ["…"]

        element_type = spec.element_type

        # Count prefix for multiple elements
        # Skip count for comments/docstrings - consecutive comments form a semantic unit
        show_count = spec.count > 1 and element_type not in ("comment", "docstring")
        if show_count:
            parts.append(str(spec.count))

        # Element type with proper formatting
        display_type = element_type.replace("_", " ")
        display_type = _pluralize(display_type, spec.count) if show_count else display_type
        parts.append(display_type)

        # Action word
        parts.append(spec.action.value)

        # Lines suffix (only for body types with explicit lines_removed > 1)
        if spec.lines_removed > 1 and element_type.endswith("_body"):
            parts.append(f"({spec.lines_removed} lines)")

        return " ".join(parts)
    
    # ============= Collapsing and finalization =============

    def raw_edits(self) -> List[PlaceholderSpec]:
        """
        Return raw edits for evaluation in the budget system.
        """
        return self.placeholders

    def finalize_edits(self) -> Tuple[List[Tuple[PlaceholderSpec, str]], Dict[str, Any]]:
        """
        Finalize all edits with collapsing.

        Returns:
            (collapsed_edits, stats)
        """
        # Perform placeholder collapsing
        collapsed_specs = self._collapse_placeholders()

        # Generate edits based on collapsed placeholders
        collapsed_edits = [
            (spec, self._generate_placeholder_text(spec) if self.placeholder_style != "none" else "")
            for spec in collapsed_specs
        ]

        # Collect statistics
        stats = self._calculate_stats(collapsed_specs)

        return collapsed_edits, stats

    def _collapse_placeholders(self) -> List[PlaceholderSpec]:
        """
        Collapse adjacent placeholders of the same type.
        Works at data level, without text parsing.
        """
        if not self.placeholders:
            return []

        # Sort by position
        sorted_placeholders = sorted(self.placeholders, key=lambda p: p.position_key)

        collapsed = []
        current_group = [sorted_placeholders[0]]

        for placeholder in sorted_placeholders[1:]:
            # Check if can merge with current group
            if current_group and current_group[-1].can_merge_with(placeholder, self.raw_text):
                current_group.append(placeholder)
            else:
                # Finalize current group
                collapsed.append(self._merge_group(current_group))
                current_group = [placeholder]

        # Don't forget last group
        if current_group:
            collapsed.append(self._merge_group(current_group))

        return collapsed

    def _merge_group(self, group: List[PlaceholderSpec]) -> PlaceholderSpec:
        """Merge group of placeholders into one."""
        if len(group) == 1:
            return group[0]

        # Sequentially merge all placeholders in group
        result = group[0]
        for placeholder in group[1:]:
            result = result.merge_with(placeholder, self.raw_text)

        return result

    def _calculate_stats(self, specs: List[PlaceholderSpec]) -> Dict[str, Any]:
        """Calculate placeholder statistics."""
        stats: Dict[str, Any] = {
            "placeholders_inserted": len(specs),
            "total_lines_removed": sum(spec.lines_removed for spec in specs),
            "placeholders_by_type": {}
        }

        # Group by types
        for spec in specs:
            etype = spec.element_type
            if etype not in stats["placeholders_by_type"]:
                stats["placeholders_by_type"][etype] = 0
            stats["placeholders_by_type"][etype] += spec.count

        return stats


# ============= Factory functions =============

def create_placeholder_manager(
    raw_text: str,
    comment_style: CommentStyle,
    placeholder_style: str
) -> PlaceholderManager:
    """
    Create PlaceholderManager from CommentStyle.

    Args:
        raw_text: source text of document
        comment_style: CommentStyle instance with comment markers
        placeholder_style: Placeholder style
    """
    return PlaceholderManager(raw_text, comment_style, placeholder_style)

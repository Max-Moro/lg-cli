"""
Centralized placeholder management system for language adapters.
Provides unified API and intelligent placeholder collapsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from .tree_sitter_support import Node
from .comment_style import CommentStyle


@dataclass
class PlaceholderSpec:
    """
    Placeholder specification with metadata.
    Stores structured placeholder information without binding to a specific format.
    """
    # Position in file
    start_char: int
    end_char: int
    start_line: int
    end_line: int

    # Placeholder type
    placeholder_type: str  # "function_body", "method_body", "import", "comment", "literal", etc.

    # Placeholder indentation (tabulation)
    placeholder_prefix: str = ""

    # Metrics
    lines_removed: int = 0
    chars_removed: int = 0
    count: int = 1  # Number of elements (for imports, comments)
    
    def __post_init__(self):
        # Calculate metrics if not passed
        if self.lines_removed == 0:
            self.lines_removed = max(0, self.end_line - self.start_line + 1)
        if self.chars_removed == 0:
            self.chars_removed = max(0, self.end_char - self.start_char)
    
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
        return self.start_line, self.start_char
    
    def can_merge_with(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Check if this placeholder can be merged with another.

        Merge conditions:
        - Same placeholder type
        - Suitable types
        - No significant content between placeholders
        """
        if self.placeholder_type != other.placeholder_type:
            return False

        # Can collapse placeholders for imports, comments, docstrings, functions, methods, classes, interfaces and types.
        # Cannot collapse placeholders for literals, function/method bodies.
        if self.placeholder_type in ["function_body", "method_body"]:
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
    
    def merge_with(self, other: PlaceholderSpec, source_text) -> PlaceholderSpec:
        """Create merged placeholder."""
        if not self.can_merge_with(other, source_text):
            raise ValueError("Cannot merge incompatible placeholders")

        # Merged boundaries
        start_char = min(self.start_char, other.start_char)
        end_char = max(self.end_char, other.end_char)
        start_line = min(self.start_line, other.start_line)
        end_line = max(self.end_line, other.end_line)
        
        return PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=self.placeholder_type,
            placeholder_prefix=self.placeholder_prefix,
            lines_removed=self.lines_removed + other.lines_removed,
            chars_removed=self.chars_removed + other.chars_removed,
            count=self.count + other.count,
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
    
    # ============= Simple API for adding placeholders =============

    def add_placeholder(self, placeholder_type: str, start_char: int, end_char: int, start_line: int, end_line: int,
                        placeholder_prefix: str = "", count: int = 1) -> None:
        """Add custom placeholder with explicit coordinates."""
        spec = PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=placeholder_type,
            placeholder_prefix=placeholder_prefix,
            count=count,
        )
        
        self._add_placeholder_with_priority(spec)

    def add_placeholder_for_node(self, placeholder_type: str, node: Node, doc, count: int = 1) -> None:
        """Add placeholder for node."""
        spec = self._create_spec_from_node(node, doc, placeholder_type, count=count)
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
    
    def _create_spec_from_node(self, node: Node, doc, placeholder_type: str, count: int = 1) -> PlaceholderSpec:
        """Create PlaceholderSpec from Tree-sitter node."""
        start_char, end_char = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)

        return PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=placeholder_type,
            placeholder_prefix="",
            count=count,
        )

    def _generate_placeholder_text(self, spec: PlaceholderSpec) -> str:
        """Generate placeholder text based on type and style."""
        content = self._get_placeholder_content(spec)

        # For docstrings always use native language wrapping
        if spec.placeholder_type == "docstring":
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
        """Generate placeholder content based on type and metrics."""
        ptype = spec.placeholder_type
        count = spec.count
        lines = spec.lines_removed
        _chars_removed = spec.chars_removed

        # Basic templates for different types
        if ptype == "function_body":
            if lines > 1:
                return f"… function body omitted ({lines} lines)"
            else:
                return "… function body omitted"
        
        elif ptype == "method_body":
            if lines > 1:
                return f"… method body omitted ({lines} lines)"
            else:
                return "… method body omitted"
        
        elif ptype == "comment":
            return "… comment omitted"

        elif ptype == "docstring":
            return "… docstring omitted"
        
        elif ptype == "import":
            if count > 1:
                return f"… {count} imports omitted"
            else:
                return "… import omitted"
        
        elif ptype == "function":
            if count > 1:
                return f"… {count} functions omitted"
            else:
                return "… function omitted"
        
        elif ptype == "method":
            if count > 1:
                return f"… {count} methods omitted"
            else:
                return "… method omitted"
        
        elif ptype == "class":
            if count > 1:
                return f"… {count} classes omitted"
            else:
                return "… class omitted"
        
        elif ptype == "interface":
            if count > 1:
                return f"… {count} interfaces omitted"
            else:
                return "… interface omitted"
        
        elif ptype == "type":
            if count > 1:
                return f"… {count} types omitted"
            else:
                return "… type omitted"
        
        else:
            # Generic template for unknown types
            if count > 1:
                return f"… {count} {ptype}s omitted"
            elif lines > 1:
                return f"… {ptype} omitted ({lines} lines)"
            else:
                return f"… {ptype} omitted"
    
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
        stats = {
            "placeholders_inserted": len(specs),
            "total_lines_removed": sum(spec.lines_removed for spec in specs),
            "total_chars_removed": sum(spec.chars_removed for spec in specs),
            "placeholders_by_type": {}
        }

        # Group by types
        for spec in specs:
            ptype = spec.placeholder_type
            if ptype not in stats["placeholders_by_type"]:
                stats["placeholders_by_type"][ptype] = 0
            stats["placeholders_by_type"][ptype] += spec.count

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

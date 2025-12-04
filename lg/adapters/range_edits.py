"""
Range-based text editing system for code transformations.
Provides safe text manipulation while preserving formatting and structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class TextRange:
    """Represents a range in text by character positions."""
    start_char: int
    end_char: int
    
    def __post_init__(self):
        if self.start_char > self.end_char:
            raise ValueError(f"Invalid range: start_char ({self.start_char}) > end_char ({self.end_char})")
    
    @property
    def length(self) -> int:
        return self.end_char - self.start_char
    
    def overlaps(self, other: TextRange) -> bool:
        """Check if this range overlaps with another."""
        return not (self.end_char <= other.start_char or other.end_char <= self.start_char)
    
    def contains(self, other: TextRange) -> bool:
        """Check if this range completely contains another."""
        return self.start_char <= other.start_char and other.end_char <= self.end_char


@dataclass
class Edit:
    """Represents a single text edit operation using character positions."""
    range: TextRange
    replacement: str
    type: Optional[str] # Type for counter in metadata
    is_insertion: bool = False  # True if this is an insertion operation (range.start_char == range.end_char)


class RangeEditor:
    """
    Unicode-safe range-based text editor that works with character positions.
    This is the new architecture that avoids UTF-8 boundary issues.
    """
    
    def __init__(self, original_text: str):
        self.original_text = original_text
        self.edits: List[Edit] = []
    
    def add_edit(self, start_char: int, end_char: int, replacement: str, edit_type: Optional[str]) -> None:
        """Add an edit operation using character positions."""
        char_range = TextRange(start_char, end_char)

        # New policy: wider edits always win
        new_width = char_range.length

        # Check all existing edits
        edits_to_remove = []
        for i, existing in enumerate(self.edits):
            if char_range.overlaps(existing.range):
                existing_width = existing.range.length

                if new_width > existing_width:
                    # New edit is wider - remove existing one
                    edits_to_remove.append(i)
                elif new_width < existing_width:
                    # New edit is narrower - skip it
                    return
                else:
                    # Same width - first wins (skip new one)
                    return

        # Remove absorbed edits (in reverse order to avoid index shift)
        for i in reversed(edits_to_remove):
            del self.edits[i]

        edit = Edit(char_range, replacement, edit_type)
        self.edits.append(edit)

    def add_deletion(self, start_char: int, end_char: int, edit_type: Optional[str]) -> None:
        """Add a deletion operation (empty replacement)."""
        self.add_edit(start_char, end_char, "", edit_type)

    def add_replacement(self, start_char: int, end_char: int, replacement: str, edit_type: Optional[str]) -> None:
        """Add a replacement operation."""
        self.add_edit(start_char, end_char, replacement, edit_type)

    def add_insertion(self, position_char: int, content: str, edit_type: Optional[str]) -> None:
        """
        Add an insertion operation after the specified character position.

        Args:
            position_char: Character position after which to insert content
            content: Content to insert
            edit_type: Type for statistics tracking
        """
        # For insertion start_char == end_char (zero-length range)
        char_range = TextRange(position_char, position_char)

        # New policy: wider edits always win
        # Insertion has zero width, so any non-insertion will absorb it
        edits_to_remove = []

        for i, existing in enumerate(self.edits):
            if existing.is_insertion:
                # Two insertions at same position - first wins
                if existing.range.start_char == position_char:
                    return
            else:
                # Insertion overlaps with replacement/deletion if position is inside range
                if existing.range.start_char < position_char < existing.range.end_char:
                    # Any non-insertion is wider than insertion (zero width) - absorbs it
                    return

        # Remove absorbed edits (in reverse order to avoid index shift)
        for i in reversed(edits_to_remove):
            del self.edits[i]

        edit = Edit(char_range, content, edit_type, is_insertion=True)
        self.edits.append(edit)

    def add_replacement_composing_nested(
        self,
        start_char: int,
        end_char: int,
        replacement: str,
        edit_type: Optional[str]
    ) -> bool:
        """
        Add a wide replacement that composes with nested narrower edits.

        When narrow edits exist inside [start_char, end_char]:
        1. Find all nested edits
        2. Apply them to the replacement text (with coordinate translation)
        3. Add the composed result as the final replacement
        4. Remove the nested edits (they've been absorbed)

        Args:
            start_char: Start position of wide replacement
            end_char: End position of wide replacement
            replacement: New text for wide replacement
            edit_type: Type for statistics tracking

        Returns:
            True if replacement was added, False if rejected
        """
        char_range = TextRange(start_char, end_char)

        # Find all edits that are completely nested inside this range
        nested_edits = []
        for i, edit in enumerate(self.edits):
            if char_range.contains(edit.range):
                nested_edits.append((i, edit))

        if not nested_edits:
            # No nested edits - add replacement normally
            self.add_edit(start_char, end_char, replacement, edit_type)
            return True

        # Apply nested edits to replacement text
        composed_text = self._apply_nested_edits_to_text(replacement, nested_edits)

        # Remove nested edits (in reverse order to avoid index shifts)
        for i, _ in reversed(nested_edits):
            del self.edits[i]

        # Add the composed replacement
        self.add_edit(start_char, end_char, composed_text, edit_type)
        return True

    def _apply_nested_edits_to_text(
        self,
        wide_text: str,
        nested_edits: List[Tuple[int, Edit]]
    ) -> str:
        """
        Apply nested edits to the wide replacement text.

        Translates coordinates from original text to replacement text and applies edits.

        Strategy:
        1. For each nested edit, extract the original substring it replaces
        2. Search for that substring in wide_text
        3. Apply the edit at the found location

        Args:
            wide_text: The replacement text for the wide edit
            nested_edits: List of (index, Edit) tuples for nested edits

        Returns:
            Text with nested edits applied
        """
        if not nested_edits:
            return wide_text

        # Group edits by their range start position
        # For each replacement, collect insertions that immediately follow it
        edit_groups = {}  # key: replacement range, value: (replacement_edit, [insertion_edits])

        for i, edit in nested_edits:
            if not edit.is_insertion:
                # This is a replacement
                key = (edit.range.start_char, edit.range.end_char)
                if key not in edit_groups:
                    edit_groups[key] = (edit, [])

        # Add insertions to their corresponding replacements
        for i, edit in nested_edits:
            if edit.is_insertion:
                ins_pos = edit.range.start_char
                # Find replacement that this insertion follows
                for (start, end), (repl_edit, ins_list) in edit_groups.items():
                    # Insertion follows this replacement if positioned right after it
                    if end <= ins_pos <= end + 10:  # Small tolerance for offset
                        ins_list.append(edit)
                        break

        # Sort groups by position (reverse order)
        sorted_groups = sorted(edit_groups.items(), key=lambda x: x[0][0], reverse=True)

        result = wide_text

        # Apply each group: replacement + its insertions
        for (start, end), (repl_edit, ins_edits) in sorted_groups:
            original_substr = self.original_text[start:end]

            # Try exact match first
            if original_substr in result:
                pos = result.rfind(original_substr)

                # Build replacement: replacement text + insertions
                composed = repl_edit.replacement
                for ins_edit in ins_edits:
                    composed += ins_edit.replacement

                result = result[:pos] + composed + result[pos + len(original_substr):]
            else:
                # Try trimming whitespace from original_substr
                trimmed_substr = original_substr.strip()
                if trimmed_substr and trimmed_substr in result:
                    pos = result.rfind(trimmed_substr)
                    after_pos = pos + len(trimmed_substr)

                    # Build replacement: replacement text + insertions
                    composed = repl_edit.replacement
                    for ins_edit in ins_edits:
                        composed += ins_edit.replacement

                    result = result[:pos] + composed + result[after_pos:]
            # If not found, element was removed by DFS - skip

        return result

    def validate_edits(self) -> List[str]:
        """
        Validate that all edits are within bounds.
        Overlap conflicts are filtered at add_edit stage (width-based policy).
        """
        errors = []

        # Check bounds only
        for i, edit in enumerate(self.edits):
            if edit.range.start_char < 0:
                errors.append(f"Edit {i}: start_char ({edit.range.start_char}) is negative")
            if edit.range.end_char > len(self.original_text):
                errors.append(f"Edit {i}: end_char ({edit.range.end_char}) exceeds text length ({len(self.original_text)})")

        return errors
    
    def apply_edits(self) -> Tuple[str, Dict[str, Any]]:
        """
        Apply all edits and return the modified text and statistics.

        Returns:
            Tuple of (modified_text, statistics)
        """
        # Validate edits first
        validation_errors = self.validate_edits()
        if validation_errors:
            raise ValueError(f"Edit validation failed: {'; '.join(validation_errors)}")

        if not self.edits:
            return self.original_text, {"edits_applied": 0, "bytes_removed": 0, "bytes_added": 0}

        # Sort all edits by position (reverse order for safe application)
        sorted_edits = sorted(self.edits, key=lambda e: e.range.start_char, reverse=True)

        result_text = self.original_text
        stats = {
            "edits_applied": len(self.edits),
            "bytes_removed": 0,
            "bytes_added": 0,
            "lines_removed": 0,
            "placeholders_inserted": 0,
        }

        # Apply all edits from end to beginning
        for edit in sorted_edits:
            if edit.is_insertion:
                # For insertion: insert content after specified position
                result_text = result_text[:edit.range.start_char] + edit.replacement + result_text[edit.range.start_char:]
                stats["bytes_added"] += len(edit.replacement.encode('utf-8'))
            else:
                # For replacement/deletion: standard logic
                original_chunk = result_text[edit.range.start_char:edit.range.end_char]

                # Preserve trailing whitespace (spaces, tabs, newlines) from original chunk
                replacement_text = edit.replacement
                if replacement_text:  # Only preserve whitespace if replacement is not empty
                    # Extract all trailing whitespace from original chunk
                    i = len(original_chunk) - 1
                    while i >= 0 and original_chunk[i] in ' \t\n\r':
                        i -= 1
                    trailing_whitespace = original_chunk[i + 1:]

                    # Append trailing whitespace if replacement doesn't already end with it
                    if trailing_whitespace and not replacement_text.endswith(trailing_whitespace):
                        replacement_text += trailing_whitespace

                result_text = result_text[:edit.range.start_char] + replacement_text + result_text[edit.range.end_char:]

                stats["bytes_removed"] += len(original_chunk.encode('utf-8'))
                stats["bytes_added"] += len(replacement_text.encode('utf-8'))
                stats["lines_removed"] += original_chunk.count('\n')

        # Calculate net change
        stats["bytes_saved"] = stats["bytes_removed"] - stats["bytes_added"]

        return result_text, stats
    
    def get_edit_summary(self) -> Dict[str, Any]:
        """Get summary of planned edits without applying them."""
        # For insertions range.length = 0, so bytes_removed = 0
        total_bytes_removed = sum(len(self.original_text[edit.range.start_char:edit.range.end_char].encode('utf-8')) for edit in self.edits if not edit.is_insertion)
        total_bytes_added = sum(len(edit.replacement.encode('utf-8')) for edit in self.edits)
        
        edit_types = {}
        for edit in self.edits:
            if edit.type:
                edit_types[edit.type] = edit_types.get(edit.type, 0) + 1
        
        return {
            "total_edits": len(self.edits),
            "bytes_to_remove": total_bytes_removed,
            "bytes_to_add": total_bytes_added,
            "net_savings": total_bytes_removed - total_bytes_added,
            "edit_types": edit_types,
        }


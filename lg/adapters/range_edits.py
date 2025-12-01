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


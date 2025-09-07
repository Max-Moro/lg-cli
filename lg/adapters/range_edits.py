"""
Range-based text editing system for code transformations.
Provides safe text manipulation while preserving formatting and structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any


@dataclass
class TextRange:
    """Represents a range in text by byte offsets."""
    start_byte: int
    end_byte: int
    
    def __post_init__(self):
        if self.start_byte > self.end_byte:
            raise ValueError(f"Invalid range: start_byte ({self.start_byte}) > end_byte ({self.end_byte})")
    
    @property
    def length(self) -> int:
        return self.end_byte - self.start_byte
    
    def overlaps(self, other: "TextRange") -> bool:
        """Check if this range overlaps with another."""
        return not (self.end_byte <= other.start_byte or other.end_byte <= self.start_byte)
    
    def contains(self, other: "TextRange") -> bool:
        """Check if this range completely contains another."""
        return self.start_byte <= other.start_byte and other.end_byte <= self.end_byte


@dataclass
class Edit:
    """Represents a single text edit operation."""
    range: TextRange
    replacement: str
    metadata: Dict[str, Any]
    
    @property
    def removes_text(self) -> bool:
        """True if this edit removes text (replacement is shorter than original)."""
        return len(self.replacement.encode('utf-8')) < self.range.length
    
    @property
    def is_deletion(self) -> bool:
        """True if this edit is a pure deletion (empty replacement)."""
        return len(self.replacement) == 0


class RangeEditor:
    """
    Safe range-based text editor that applies multiple edits while preserving structure.
    """
    
    def __init__(self, original_text: str):
        self.original_text = original_text
        self.original_bytes = original_text.encode('utf-8')
        self.edits: List[Edit] = []
    
    def add_edit(self, start_byte: int, end_byte: int, replacement: str, **metadata) -> None:
        """Add an edit operation."""
        text_range = TextRange(start_byte, end_byte)

        # First-wins: если новая правка перекрывается с любой уже добавленной — тихо пропускаем её.
        for existing in self.edits:
            if text_range.overlaps(existing.range):
                return

        edit = Edit(text_range, replacement, metadata)
        self.edits.append(edit)
    
    def add_deletion(self, start_byte: int, end_byte: int, **metadata) -> None:
        """Add a deletion operation (empty replacement)."""
        self.add_edit(start_byte, end_byte, "", **metadata)
    
    def add_replacement(self, start_byte: int, end_byte: int, replacement: str, **metadata) -> None:
        """Add a replacement operation."""
        self.add_edit(start_byte, end_byte, replacement, **metadata)
    
    def validate_edits(self) -> List[str]:
        """
        Validate that all edits are within bounds.
        Overlap conflicts отфильтровываются на этапе add_edit (first-wins).
        """
        errors = []

        # Check bounds only
        for i, edit in enumerate(self.edits):
            if edit.range.start_byte < 0:
                errors.append(f"Edit {i}: start_byte ({edit.range.start_byte}) is negative")
            if edit.range.end_byte > len(self.original_bytes):
                errors.append(f"Edit {i}: end_byte ({edit.range.end_byte}) exceeds text length ({len(self.original_bytes)})")

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
        
        # Sort edits by start position (reverse order for safe application)
        sorted_edits = sorted(self.edits, key=lambda e: e.range.start_byte, reverse=True)
        
        # Apply edits from end to beginning to maintain byte offsets
        result_bytes = bytearray(self.original_bytes)
        stats = {
            "edits_applied": len(sorted_edits),
            "bytes_removed": 0,
            "bytes_added": 0,
            "lines_removed": 0,
            "placeholders_inserted": 0,
        }
        
        for edit in sorted_edits:
            # Calculate statistics
            original_chunk = result_bytes[edit.range.start_byte:edit.range.end_byte]
            replacement_bytes = edit.replacement.encode('utf-8')
            
            stats["bytes_removed"] += len(original_chunk)
            stats["bytes_added"] += len(replacement_bytes)
            stats["lines_removed"] += original_chunk.count(b'\n')
            
            if edit.metadata.get("is_placeholder", False):
                stats["placeholders_inserted"] += 1
            
            # Apply the edit
            result_bytes[edit.range.start_byte:edit.range.end_byte] = replacement_bytes
        
        # Calculate net change
        stats["bytes_saved"] = stats["bytes_removed"] - stats["bytes_added"]
        
        try:
            result_text = result_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode result text: {e}")
        
        return result_text, stats
    
    def get_edit_summary(self) -> Dict[str, Any]:
        """Get summary of planned edits without applying them."""
        total_bytes_removed = sum(edit.range.length for edit in self.edits)
        total_bytes_added = sum(len(edit.replacement.encode('utf-8')) for edit in self.edits)
        
        edit_types = {}
        for edit in self.edits:
            edit_type = edit.metadata.get("type", "unknown")
            edit_types[edit_type] = edit_types.get(edit_type, 0) + 1
        
        return {
            "total_edits": len(self.edits),
            "bytes_to_remove": total_bytes_removed,
            "bytes_to_add": total_bytes_added,
            "net_savings": total_bytes_removed - total_bytes_added,
            "edit_types": edit_types,
        }


class PlaceholderGenerator:
    """Generator for code placeholders with consistent formatting."""
    
    def __init__(self, comment_style: Tuple[str, Tuple[str, str]]):
        """
        Initialize with comment style for the language.
        
        Args:
            comment_style: Tuple of (single_line, (multi_start, multi_end))
                          e.g., ("//", ("/*", "*/")) for C-style
                          e.g., ("#", ('"""', '"""')) for Python
        """
        self.single_line_comment = comment_style[0]
        self.multi_line_start, self.multi_line_end = comment_style[1]
    
    def create_function_placeholder(
        self,
        lines_removed: int,
        bytes_removed: int,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for a removed function body."""
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} … body omitted ({lines_removed})"
        elif style == "block":
            return f"{self.multi_line_start} … body omitted ({lines_removed}) {self.multi_line_end}"
        else:
            return ""
    
    def create_method_placeholder(
        self,
        lines_removed: int,
        bytes_removed: int,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for a removed method body."""
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} … method omitted ({lines_removed})"
        elif style == "block":
            return f"{self.multi_line_start} … method omitted ({lines_removed}) {self.multi_line_end}"
        else:
            return ""
    
    def create_import_placeholder(
        self,
        count: int,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for summarized imports."""
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} … {count} imports omitted"
        elif style == "block":
            return f"{self.multi_line_start} … {count} imports omitted {self.multi_line_end}"
        else:
            return ""
    
    def create_literal_placeholder(
        self,
        literal_type: str,
        bytes_removed: int,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for truncated literals."""
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} … {literal_type} data omitted ({bytes_removed} bytes)"
        elif style == "block":
            return f"{self.multi_line_start} … {literal_type} data omitted ({bytes_removed} bytes) {self.multi_line_end}"
        else:
            return ""
    
    def create_comment_placeholder(
        self,
        comment_type: str,
        count: int = 1,
        lines_removed: int = 0,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for removed comments."""
        if count == 1:
            content = f"… {comment_type} omitted"
        else:
            content = f"… {count} {comment_type}s omitted"
            
        if lines_removed > 0:
            content += f" ({lines_removed})"
            
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} {content}"
        elif style == "block":
            return f"{self.multi_line_start} {content} {self.multi_line_end}"
        else:
            return ""
    
    def create_docstring_placeholder(
        self,
        policy: str,
        lines_removed: int = 0,
        style: str = "inline"
    ) -> str:
        """Create a placeholder for processed docstrings."""
        if policy == "strip_all":
            content = f"… docstring omitted ({lines_removed})"
        elif policy == "keep_first_sentence":
            content = f"… docstring truncated ({lines_removed})"
        else:
            content = f"… docstring processed ({lines_removed})"
            
        if style == "inline" or style == "auto":
            return f"{self.single_line_comment} {content}"
        elif style == "block":
            return f"{self.multi_line_start} {content} {self.multi_line_end}"
        else:
            return ""

    def create_custom_placeholder(
        self,
        template: str,
        variables: Dict[str, Any],
        style: str = "inline"
    ) -> str:
        """Create a custom placeholder using a template."""
        try:
            content = template.format(**variables)
            if style == "block" and not content.startswith(self.multi_line_start):
                return f"{self.multi_line_start} {content} {self.multi_line_end}"
            return content
        except KeyError as e:
            # Fallback if template variables are missing
            return f"{self.single_line_comment} … placeholder error: {e}"

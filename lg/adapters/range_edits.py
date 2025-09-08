"""
Range-based text editing system for code transformations.
Provides safe text manipulation while preserving formatting and structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


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


@dataclass
class PlaceholderInfo:
    """Information about a parsed placeholder."""
    indent: str                    # Leading whitespace
    comment_style: str            # '#', '//', or '/*'
    placeholder_type: str         # 'comment', 'import', 'function', 'method', 'literal'
    count: int = 1               # Number of items (for aggregation)
    lines: Optional[int] = None   # Number of lines removed
    bytes: Optional[int] = None   # Number of bytes removed
    unit: Optional[str] = None    # Unit of measurement ('bytes', 'lines', etc.)
    
    def can_aggregate_with(self, other: 'PlaceholderInfo') -> bool:
        """Check if this placeholder can be aggregated with another."""
        return (
            self.indent == other.indent and
            self.comment_style == other.comment_style and
            self.placeholder_type == other.placeholder_type
        )
    
    def aggregate_with(self, other: 'PlaceholderInfo') -> 'PlaceholderInfo':
        """Create a new aggregated placeholder."""
        if not self.can_aggregate_with(other):
            raise ValueError("Cannot aggregate incompatible placeholders")
        
        return PlaceholderInfo(
            indent=self.indent,
            comment_style=self.comment_style,
            placeholder_type=self.placeholder_type,
            count=self.count + other.count,
            lines=(self.lines or 0) + (other.lines or 0) if self.lines or other.lines else None,
            bytes=(self.bytes or 0) + (other.bytes or 0) if self.bytes or other.bytes else None,
            unit=self.unit or other.unit
        )


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
        
        # Post-process: collapse consecutive placeholders
        result_text = self._collapse_placeholders(result_text)
        
        return result_text, stats
    
    def _collapse_placeholders(self, text: str) -> str:
        """
        Collapse consecutive placeholders into single consolidated placeholders.
        
        This handles all types of placeholders (comments, imports, functions, etc.) and prevents
        having multiple consecutive lines like:
        # … comment omitted
        # … comment omitted  
        # … comment omitted
        
        Instead, we get:
        # … 3 comments omitted
        
        Also aggregates numerical values:
        # … 5 imports omitted
        # … 6 imports omitted
        becomes:
        # … 11 imports omitted
        
        Args:
            text: Text content to process
            
        Returns:
            Text with collapsed placeholders
        """
        lines = text.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this line is any type of placeholder
            placeholder_info = self._match_placeholder(line)
            
            if placeholder_info:
                # Found a placeholder - collect consecutive ones
                consecutive_placeholders = [placeholder_info]
                j = i + 1
                
                # Look ahead for more consecutive placeholders of the same type
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Skip empty lines - they don't break the sequence
                    if not next_line.strip():
                        j += 1
                        continue
                    
                    # Check if next line is a compatible placeholder
                    next_placeholder = self._match_placeholder(next_line)
                    if next_placeholder and placeholder_info.can_aggregate_with(next_placeholder):
                        consecutive_placeholders.append(next_placeholder)
                        j += 1
                    else:
                        break
                
                # If we found multiple consecutive placeholders, collapse them
                if len(consecutive_placeholders) > 1:
                    # Aggregate all placeholder info
                    aggregated_info = consecutive_placeholders[0]
                    for ph in consecutive_placeholders[1:]:
                        aggregated_info = aggregated_info.aggregate_with(ph)
                    
                    # Create collapsed placeholder
                    collapsed = self._create_collapsed_placeholder_from_info(aggregated_info)
                    result_lines.append(collapsed)
                    
                    i = j
                else:
                    # Single placeholder - keep as is
                    result_lines.append(line)
                    i += 1
            else:
                # Not a placeholder - keep as is
                result_lines.append(line)
                i += 1
        
        return '\n'.join(result_lines)
    
    def _match_placeholder(self, line: str) -> Optional[PlaceholderInfo]:
        """
        Check if a line contains any type of placeholder and extract its components.
        
        Handles various placeholder formats:
        - # … comment omitted
        - # … 5 imports omitted  
        - # … body omitted (15)
        - # … string data omitted (256 bytes)
        
        Returns:
            PlaceholderInfo object or None if no placeholder found
        """
        import re
        
        # Comprehensive patterns for all placeholder types
        patterns = [
            # Pattern 1: Simple format - # … TYPE omitted
            (r'^(\s*)(#|//|/\*)\s*…\s*(\w+)\s+omitted(?:\s*\*/)?$', 'simple'),
            
            # Pattern 2: Count format - # … N TYPE omitted (imports)  
            (r'^(\s*)(#|//|/\*)\s*…\s*(\d+)\s+(\w+)\s+omitted(?:\s*\*/)?$', 'count_before'),
            
            # Pattern 3: Lines format - # … TYPE omitted (N)
            (r'^(\s*)(#|//|/\*)\s*…\s*(\w+)\s+omitted\s*\((\d+)\)(?:\s*\*/)?$', 'lines_after'),
            
            # Pattern 4: Data format - # … TYPE data omitted (N bytes)
            (r'^(\s*)(#|//|/\*)\s*…\s*(\w+)\s+data\s+omitted\s*\((\d+)\s+(\w+)\)(?:\s*\*/)?$', 'data_with_unit'),
            
            # Pattern 5: Multiple count format - # … N TYPEs omitted (plural)
            (r'^(\s*)(#|//|/\*)\s*…\s*(\d+)\s+(\w+)s\s+omitted(?:\s*\*/)?$', 'plural_count'),
        ]
        
        for pattern, format_type in patterns:
            match = re.match(pattern, line)
            if match:
                return self._parse_placeholder_match(match, format_type)
        
        return None
    
    def _parse_placeholder_match(self, match, format_type: str) -> PlaceholderInfo:
        """Parse a regex match into PlaceholderInfo based on format type."""
        indent = match.group(1)
        comment_prefix = match.group(2)
        
        # Determine comment style
        if comment_prefix == '#':
            comment_style = '#'
        elif comment_prefix == '//':
            comment_style = '//'
        elif comment_prefix.startswith('/*'):
            comment_style = '/*'
        else:
            comment_style = comment_prefix
        
        if format_type == 'simple':
            # # … comment omitted
            placeholder_type = match.group(3)
            return PlaceholderInfo(
                indent=indent,
                comment_style=comment_style,
                placeholder_type=placeholder_type,
                count=1
            )
        
        elif format_type == 'count_before':
            # # … 5 imports omitted
            count = int(match.group(3))
            placeholder_type = match.group(4)
            return PlaceholderInfo(
                indent=indent,
                comment_style=comment_style,
                placeholder_type=placeholder_type,
                count=count
            )
        
        elif format_type == 'lines_after':
            # # … body omitted (15)
            placeholder_type = match.group(3)
            lines = int(match.group(4))
            return PlaceholderInfo(
                indent=indent,
                comment_style=comment_style,
                placeholder_type=placeholder_type,
                count=1,
                lines=lines
            )
        
        elif format_type == 'data_with_unit':
            # # … string data omitted (256 bytes)
            placeholder_type = match.group(3)
            amount = int(match.group(4))
            unit = match.group(5)
            return PlaceholderInfo(
                indent=indent,
                comment_style=comment_style,
                placeholder_type=placeholder_type,
                count=1,
                bytes=amount if unit == 'bytes' else None,
                lines=amount if unit == 'lines' else None,
                unit=unit
            )
        
        elif format_type == 'plural_count':
            # # … 3 comments omitted
            count = int(match.group(3))
            placeholder_type = match.group(4)  # Singular form (comment, not comments)
            return PlaceholderInfo(
                indent=indent,
                comment_style=comment_style,
                placeholder_type=placeholder_type,
                count=count
            )
        
        # Fallback
        return PlaceholderInfo(
            indent=indent,
            comment_style=comment_style,
            placeholder_type='unknown',
            count=1
        )
    
    def _create_collapsed_placeholder_from_info(self, info: PlaceholderInfo) -> str:
        """
        Create a collapsed placeholder from PlaceholderInfo.
        
        Handles various aggregation formats:
        - Simple count: # … 3 comments omitted
        - Import aggregation: # … 11 imports omitted
        - Lines aggregation: # … body omitted (25 lines)
        - Bytes aggregation: # … string data omitted (512 bytes)
        
        Args:
            info: PlaceholderInfo containing aggregated data
            
        Returns:
            Formatted collapsed placeholder string
        """
        # Choose the appropriate format based on placeholder type and available data
        if info.placeholder_type == 'import' or info.count > 1:
            # For imports and multiple items, show count before type
            content = f"… {info.count} {info.placeholder_type}s omitted"
        elif info.lines and info.bytes:
            # Both lines and bytes available (rare case)
            content = f"… {info.placeholder_type} omitted ({info.lines} lines, {info.bytes} bytes)"
        elif info.lines:
            # Lines available
            if info.count > 1:
                content = f"… {info.count} {info.placeholder_type}s omitted ({info.lines} lines total)"
            else:
                content = f"… {info.placeholder_type} omitted ({info.lines} lines)"
        elif info.bytes:
            # Bytes available (for data/literals)
            if info.unit:
                content = f"… {info.placeholder_type} data omitted ({info.bytes} {info.unit})"
            else:
                content = f"… {info.placeholder_type} omitted ({info.bytes} bytes)"
        else:
            # Simple format
            if info.count > 1:
                content = f"… {info.count} {info.placeholder_type}s omitted"
            else:
                content = f"… {info.placeholder_type} omitted"
        
        # Format with comment style
        if info.comment_style == '#':
            return f"{info.indent}# {content}"
        elif info.comment_style == '//':
            return f"{info.indent}// {content}"
        elif info.comment_style == '/*':
            return f"{info.indent}/* {content} */"
        else:
            # Fallback to single-line style
            return f"{info.indent}# {content}"
    
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
        bytes_removed: int,
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

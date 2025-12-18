"""
Text utilities for comment processing.
Shared functions for sentence extraction, line boundary detection, and content cleaning.
"""

from __future__ import annotations

import re
from typing import List, Tuple


def extract_sentence(content: str) -> str:
    """
    Extract first sentence from cleaned content.

    Splits by sentence terminators (.!?) and returns first non-empty sentence.

    Args:
        content: Cleaned text content (without comment markers)

    Returns:
        First sentence or original content if no terminator found
    """
    sentences = re.split(r'[.!?]+', content)
    if sentences and len(sentences) > 1 and sentences[0].strip():
        return sentences[0].strip()
    # No sentence terminator found - return first line
    lines = content.split('\n')
    for line in lines:
        if line.strip():
            return line.strip()
    return content


def clean_multiline_comment_content(content: str) -> List[str]:
    """
    Remove leading * from each line of multi-line comment.

    Handles JSDoc, block comments, and similar formats where each line
    may start with ' * '.

    Args:
        content: Raw content between comment markers

    Returns:
        List of cleaned non-empty lines
    """
    lines = content.split('\n')
    clean_lines = []
    for line in lines:
        clean_line = re.sub(r'^\s*\*\s?', '', line)
        if clean_line.strip():
            clean_lines.append(clean_line.strip())
    return clean_lines


def get_line_range(text: str, start: int, end: int) -> Tuple[int, int]:
    """
    Extend byte range to include full line(s) with trailing newline.

    Args:
        text: Full source text
        start: Start byte position
        end: End byte position

    Returns:
        Tuple of (extended_start, extended_end) including full lines
    """
    # Move start back to line beginning
    while start > 0 and text[start - 1] not in '\r\n':
        start -= 1

    # Move end to include trailing newline
    if end < len(text):
        if text[end:end + 2] == '\r\n':
            end += 2
        elif text[end] == '\n':
            end += 1

    return start, end


def detect_base_indent(text: str, default: str = '     ') -> str:
    """
    Detect base indentation from multi-line comment.

    Looks at second line to determine indentation pattern for * markers.

    Args:
        text: Full comment text
        default: Default indentation if detection fails

    Returns:
        Detected indentation string
    """
    lines = text.split('\n')
    if len(lines) > 1:
        second_line = lines[1]
        indent_match = re.match(r'^(\s*)\*', second_line)
        if indent_match:
            return indent_match.group(1)
    return default


__all__ = [
    "extract_sentence",
    "clean_multiline_comment_content",
    "get_line_range",
    "detect_base_indent",
]

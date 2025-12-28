"""
Comment analysis infrastructure for language-specific comment processing.
Provides base classes and utilities for analyzing and processing comments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from tree_sitter import Node

from ...comment_style import CommentStyle
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class TruncationStyle:
    """Description of comment style for truncation."""
    start_marker: str           # Opening marker (e.g., "/**", '"""', "//")
    end_marker: str = ""        # Closing marker (e.g., "*/", '"""', "")
    is_multiline: bool = False  # Whether this is a multiline block comment
    base_indent: str = ""       # Indentation for multiline closing (e.g., " * ")
    ellipsis: str = "…"         # Ellipsis character


class CommentAnalyzer:
    """
    Base class for language-specific comment analyzers.

    Provides methods for identifying, extracting, and processing comments
    according to language-specific conventions.
    """

    def __init__(self, doc: TreeSitterDocument, style: CommentStyle):
        """
        Initialize the analyzer for a document.

        Args:
            doc: TreeSitterDocument instance to analyze
            style: CommentStyle instance with comment markers for this language
        """
        self.doc = doc
        self.style = style
        self._analyzed = False

    def get_comment_query(self) -> str:
        """
        Get Tree-sitter query for finding comments.

        Default returns simple "(comment) @comment".
        Override in language-specific analyzers for different node types.

        Returns:
            Tree-sitter query string with @comment captures
        """
        return "(comment) @comment"

    def get_docstring_query(self) -> str | None:
        """
        Get Tree-sitter query for finding docstrings (separate from comments).

        Returns None if language doesn't have separate docstring syntax.
        Override in language analyzers that have docstrings (Python).

        Returns:
            Tree-sitter query string with @docstring captures, or None
        """
        return None

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Determine if a comment is a documentation comment.

        Uses multiple strategies:
        1. Check if capture_name from Tree-sitter query is "docstring" or "comment.doc"
        2. Check if text starts with block documentation markers (e.g., "/**")
        3. Check if text starts with line documentation markers (e.g., "///")

        Can be overridden for language-specific logic (e.g., Go position-based detection).

        Args:
            node: AST node representing the comment
            text: Comment text content
            capture_name: Capture name from Tree-sitter query (optional)

        Returns:
            True if the comment is a documentation comment, False otherwise
        """
        # Strategy 1: Tree-sitter capture name
        if capture_name in ("docstring", "comment.doc"):
            return True

        stripped = text.strip()

        # Strategy 2: Block doc markers (e.g., /** ... */)
        doc_start, _ = self.style.doc_markers
        if doc_start and stripped.startswith(doc_start):
            return True

        # Strategy 3: Line doc markers (e.g., ///, //!)
        for marker in self.style.line_doc_markers:
            if stripped.startswith(marker):
                return True

        return False

    def get_comment_group(self, node: Node) -> Optional[List[Node]]:
        """
        Get group of consecutive comments that form a single documentation block.

        Default returns None (no grouping). Override in GroupingCommentAnalyzer
        for languages like Go and Rust where multiple line comments form one doc block.

        Args:
            node: Comment node to check

        Returns:
            List of nodes forming the group, or None if no grouping applies
        """
        return None

    def extract_first_sentence(self, text: str) -> str:
        """
        Extract first sentence from comment text.

        Handles different comment styles:
        - JSDoc style: /** ... */
        - Single-line: //
        - Multi-line: /* ... */

        Can be overridden for language-specific formatting (Python docstrings, custom formats).

        Args:
            text: Comment text to process

        Returns:
            First sentence with appropriate punctuation and formatting
        """
        from .text_utils import (
            extract_sentence,
            clean_multiline_comment_content,
            detect_base_indent,
        )

        stripped = text.strip()

        # Handle JSDoc comments (/** ... */)
        if stripped.startswith('/**'):
            return self._extract_first_sentence_block(text, '/**', '*/', extract_sentence, clean_multiline_comment_content, detect_base_indent)

        # Handle regular single-line comments
        elif text.startswith('//'):
            clean_text = text[2:].strip()
            first = extract_sentence(clean_text)
            return f"// {first}."

        # Handle regular multiline comments (/* ... */)
        elif text.startswith('/*') and text.rstrip().endswith('*/'):
            return self._extract_first_sentence_block(text, '/*', '*/', extract_sentence, clean_multiline_comment_content, detect_base_indent)

        return text  # Fallback to original text

    def _extract_first_sentence_block(
        self,
        text: str,
        start_marker: str,
        end_marker: str,
        extract_sentence,
        clean_content,
        detect_indent
    ) -> str:
        """
        Extract first sentence from block comment (/* */ or /** */).

        Args:
            text: Full comment text
            start_marker: Opening marker (/* or /**)
            end_marker: Closing marker (*/)
            extract_sentence: Utility function for sentence extraction
            clean_content: Utility function for cleaning multiline content
            detect_indent: Utility function for detecting indentation

        Returns:
            First sentence with proper block comment formatting
        """
        is_multiline = '\n' in text
        base_indent = detect_indent(text, ' ') if is_multiline else ' '

        # Extract content between markers
        pattern = rf'{re.escape(start_marker)}\s*(.*?)\s*{re.escape(end_marker)}'
        match = re.match(pattern, text, re.DOTALL)

        if not match:
            return text

        content = match.group(1)
        clean_lines = clean_content(content)

        if not clean_lines:
            return text

        # Get first sentence from cleaned content
        full_text = ' '.join(clean_lines)
        first = extract_sentence(full_text)

        # If no sentence terminator found (utility returned full text), use first line
        if first == full_text and clean_lines:
            first = clean_lines[0].rstrip('.')

        # Format output based on style
        if is_multiline:
            return f'{start_marker}\n{base_indent}* {first}.\n{base_indent}*/'
        else:
            return f"{start_marker} {first}. {end_marker}"

    def truncate_comment(self, text: str, max_tokens: int, tokenizer) -> str:
        """
        Truncate comment while preserving proper closing tags.

        Args:
            text: Comment text to truncate
            max_tokens: Maximum allowed tokens
            tokenizer: TokenService for counting and truncating tokens

        Returns:
            Properly truncated comment with correct closing tags
        """
        # Check if already within budget
        if tokenizer.count_text_cached(text) <= max_tokens:
            return text

        # Detect comment style
        style = self._detect_truncation_style(text)

        if style is None:
            # Fallback: simple truncation with ellipsis
            ellipsis_tokens = tokenizer.count_text_cached("…")
            content_budget = max(1, max_tokens - ellipsis_tokens)
            if content_budget < 1:
                return "…"
            truncated = tokenizer.truncate_to_tokens(text, content_budget)
            return f"{truncated}…"

        # Build closing sequence based on comment type
        if style.end_marker:
            if style.is_multiline and style.base_indent:
                # Multiline block comment: "…\n<indent>*/"
                closing = f"\n{style.base_indent}{style.end_marker}"
                ellipsis_tokens = tokenizer.count_text_cached(style.ellipsis)
                closing_tokens = tokenizer.count_text_cached(closing)
                content_budget = max(1, max_tokens - closing_tokens - ellipsis_tokens)

                if content_budget < 1:
                    return f"{style.start_marker}\n{style.base_indent}* {style.ellipsis}\n{style.base_indent}{style.end_marker}"

                truncated = tokenizer.truncate_to_tokens(text, content_budget)
                return f"{truncated}{style.ellipsis}{closing}"
            else:
                # Single-line block: "content…<end_marker>"
                closing = f"{style.ellipsis}{style.end_marker}"
        else:
            # Line comment (no closing marker): just ellipsis
            closing = style.ellipsis

        closing_tokens = tokenizer.count_text_cached(closing)
        content_budget = max(1, max_tokens - closing_tokens)

        if content_budget < 1:
            # Not enough budget even for minimal content
            if style.end_marker:
                return f"{style.start_marker}{style.ellipsis}{style.end_marker}"
            else:
                return f"{style.start_marker}{style.ellipsis}"

        # Truncate content
        truncated = tokenizer.truncate_to_tokens(text, content_budget)
        return f"{truncated}{closing}"

    def _detect_truncation_style(self, text: str) -> Optional[TruncationStyle]:
        """
        Detect comment style for truncation.

        Override in subclasses for language-specific styles.
        Default implementation handles C-style comments.
        """
        from .text_utils import detect_base_indent

        stripped = text.strip()

        # JSDoc/block doc comments (/** ... */)
        if stripped.startswith('/**'):
            is_multiline = '\n' in text
            base_indent = detect_base_indent(text, ' ') if is_multiline else ''
            return TruncationStyle(
                start_marker='/**',
                end_marker='*/',
                is_multiline=is_multiline,
                base_indent=base_indent
            )

        # Regular multiline comments (/* ... */)
        if stripped.startswith('/*') and stripped.endswith('*/'):
            is_multiline = '\n' in text
            base_indent = detect_base_indent(text, ' ') if is_multiline else ''
            return TruncationStyle(
                start_marker='/*',
                end_marker='*/',
                is_multiline=is_multiline,
                base_indent=base_indent
            )

        # Single line comments (//)
        if text.startswith('//'):
            return TruncationStyle(
                start_marker='//',
                end_marker='',
                is_multiline=False
            )

        # Hash comments (#)
        if text.startswith('#'):
            return TruncationStyle(
                start_marker='#',
                end_marker='',
                is_multiline=False
            )

        return None  # Unknown style, use fallback

    def get_associated_comments_range(
        self,
        node: Node,
        include_leading: bool = True,
        include_trailing_inline: bool = True,
    ) -> tuple[int, int]:
        """
        Get extended byte range that includes associated comments.

        Used by PublicApiOptimizer and ImportOptimizer to capture comments
        that semantically belong to elements being removed.

        Args:
            node: Element node to find associated comments for
            include_leading: Include comments before the element (no blank lines between)
            include_trailing_inline: Include comments after element on the same line

        Returns:
            Tuple of (start_byte, end_byte) — extended range including comments.
            Returns original node range if no associated comments found.
        """
        start_byte = node.start_byte
        end_byte = node.end_byte

        if include_leading:
            start_byte = self._find_leading_comments_start(node, start_byte)

        if include_trailing_inline:
            end_byte = self._find_trailing_inline_comment_end(node, end_byte)

        return start_byte, end_byte

    def _find_leading_comments_start(self, node: Node, default_start: int) -> int:
        """
        Find start byte of leading comments before the node.

        Leading comments are comments that:
        - Appear as siblings before the node
        - Have no blank lines between them and the node
        - Form a contiguous block

        Args:
            node: Element node
            default_start: Default start byte if no leading comments

        Returns:
            Start byte of first leading comment, or default_start
        """
        parent = node.parent
        if not parent:
            return default_start

        # Find node index among siblings
        siblings = parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling.id == node.id:
                node_index = i
                break

        if node_index is None or node_index == 0:
            return default_start

        # Walk backwards through siblings to find leading comments
        leading_comment_start = default_start
        prev_end_byte = node.start_byte

        for i in range(node_index - 1, -1, -1):
            sibling = siblings[i]

            # Check if this is a comment using node type
            is_comment = sibling.type in ("comment", "line_comment", "block_comment")

            # Fallback: check text content if type doesn't match
            if not is_comment:
                sibling_text = self.doc.get_node_text(sibling)
                is_comment = (
                    sibling_text.strip().startswith(self.style.single_line) or
                    sibling_text.strip().startswith(self.style.multi_line[0])
                )

            if not is_comment:
                break

            # Check for blank line between this comment and previous element
            text_between = self.doc.text_bytes[sibling.end_byte:prev_end_byte].decode('utf-8', errors='replace')
            if self._has_blank_line(text_between):
                break

            # This comment is associated with the node
            leading_comment_start = sibling.start_byte
            prev_end_byte = sibling.start_byte

        return leading_comment_start

    def _find_trailing_inline_comment_end(self, node: Node, default_end: int) -> int:
        """
        Find end byte of trailing inline comment (same line as node end).

        Args:
            node: Element node
            default_end: Default end byte if no trailing comment

        Returns:
            End byte after trailing comment, or default_end
        """
        # Look at bytes after node on the same line
        bytes_after = self.doc.text_bytes[node.end_byte:]

        # Find end of current line (in bytes)
        newline_pos = bytes_after.find(b'\n')
        if newline_pos == -1:
            line_remainder_bytes = bytes_after
        else:
            line_remainder_bytes = bytes_after[:newline_pos]

        # Decode to string for content analysis
        line_remainder = line_remainder_bytes.decode('utf-8', errors='replace')

        # Check if there's a comment on this line
        stripped = line_remainder.strip()
        if not stripped:
            return default_end

        # Check for single-line comment marker
        comment_start = None
        if self.style.single_line and self.style.single_line in line_remainder:
            comment_start = line_remainder.find(self.style.single_line)

        # Check for block comment that starts and ends on same line
        if self.style.multi_line[0] and self.style.multi_line[0] in line_remainder:
            block_start = line_remainder.find(self.style.multi_line[0])
            if self.style.multi_line[1] in line_remainder[block_start:]:
                if comment_start is None or block_start < comment_start:
                    comment_start = block_start

        if comment_start is not None:
            # Include the comment in the range (up to newline or end of text)
            if newline_pos == -1:
                return len(self.doc.text_bytes)
            else:
                return node.end_byte + newline_pos

        return default_end

    def _has_blank_line(self, text: str) -> bool:
        """Check if text contains a blank line (two consecutive newlines)."""
        return '\n\n' in text or '\r\n\r\n' in text


__all__ = ["CommentAnalyzer", "TruncationStyle"]

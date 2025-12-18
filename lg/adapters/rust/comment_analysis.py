"""
Rust-specific comment analyzer with doc comment detection and grouping.

Provides language-specific implementation of CommentAnalyzer for Rust.
Rust has several types of documentation comments:
- /// - outer doc comment (documents following item)
- //! - inner doc comment (documents enclosing item/module)
- /** ... */ - outer block doc comment
- /*! ... */ - inner block doc comment

Multi-line doc comments (consecutive /// or //! comments) are grouped and treated as a single block.
"""

from __future__ import annotations

import re
from typing import List, Set

from tree_sitter import Node

from ..optimizations.comments import (
    GroupingCommentAnalyzer,
    extract_sentence,
    clean_multiline_comment_content,
)


class RustCommentAnalyzer(GroupingCommentAnalyzer):
    """
    Rust-specific comment analyzer with doc comment detection and grouping.

    Rust has several doc comment types:
    - /// - outer doc comment (documents following item)
    - //! - inner doc comment (documents enclosing item/module)
    - /** - outer block doc comment
    - /*! - inner block doc comment

    Consecutive /// or //! comments that form a single documentation block are grouped together.
    """

    def extract_first_sentence(self, text: str) -> str:
        """
        Extract first sentence from Rust comment text.

        Handles Rust-specific doc comment markers (///, //!, /**, /*!).

        Args:
            text: Comment text to process

        Returns:
            First sentence with appropriate punctuation and formatting
        """
        stripped = text.strip()

        # Handle /// doc comments
        if stripped.startswith('///'):
            clean_text = stripped[3:].strip()
            first = extract_sentence(clean_text)
            return f"/// {first}."

        # Handle //! inner doc comments
        if stripped.startswith('//!'):
            clean_text = stripped[3:].strip()
            first = extract_sentence(clean_text)
            return f"//! {first}."

        # Handle /** block doc comments
        if stripped.startswith('/**'):
            return self._extract_first_sentence_block_doc(text, '/**', '*/')

        # Handle /*! inner block doc comments
        if stripped.startswith('/*!'):
            return self._extract_first_sentence_block_doc(text, '/*!', '*/')

        # Fallback to base implementation for other comment types
        return super().extract_first_sentence(text)

    def _extract_first_sentence_block_doc(self, text: str, start_marker: str, end_marker: str) -> str:
        """
        Extract first sentence from block documentation comment.

        Args:
            text: Full comment text
            start_marker: Opening marker (/** or /*!)
            end_marker: Closing marker (*/)

        Returns:
            First sentence with proper block comment formatting
        """
        # Extract content between markers
        pattern = rf'{re.escape(start_marker)}\s*(.*?)\s*{re.escape(end_marker)}'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            content = match.group(1)
            clean_lines = clean_multiline_comment_content(content)

            if clean_lines:
                full_text = ' '.join(clean_lines)
                first = extract_sentence(full_text)

                # If no sentence terminator found, use first line
                if first == full_text and clean_lines:
                    first = clean_lines[0].rstrip('.')

                return f"{start_marker} {first}. {end_marker}"

        return text

    def _analyze_all_comments(self) -> None:
        """
        Perform one-time analysis of all comments in the document.

        Groups consecutive line-based doc comments (/// and //!).
        """
        # Get all comment nodes
        comments = self.doc.query("comments")

        # Deduplicate nodes by position (Rust query returns duplicates for doc comments)
        seen_positions: Set[tuple[int, int]] = set()
        comment_nodes = []
        for node, _ in comments:
            pos = (node.start_byte, node.end_byte)
            if pos not in seen_positions:
                seen_positions.add(pos)
                comment_nodes.append(node)

        # Group consecutive doc comments
        self._comment_groups = self._group_consecutive_doc_comments(comment_nodes)
        self._doc_comment_positions = set()

        # Mark all nodes in doc comment groups
        for group in self._comment_groups:
            for node in group:
                position = (node.start_byte, node.end_byte)
                self._doc_comment_positions.add(position)

        self._analyzed = True

    def _group_consecutive_doc_comments(self, comment_nodes: List[Node]) -> List[List[Node]]:
        """
        Group consecutive line-based doc comments (/// or //!).

        Comments are consecutive if separated only by whitespace (no blank lines)
        and have the same marker type.

        Args:
            comment_nodes: List of comment nodes from Tree-sitter

        Returns:
            List of comment groups (each group is a list of nodes)
        """
        if not comment_nodes:
            return []

        groups = []
        current_group = []
        current_marker = None

        for node in comment_nodes:
            node_text = self.doc.get_node_text(node).strip()

            # Check if this is a line-based doc comment
            marker = None
            for m in self.style.line_doc_markers:
                if node_text.startswith(m):
                    marker = m
                    break

            if marker is None:
                # Not a line doc comment - finalize current group
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_marker = None
                continue

            # Check if this continues the current group
            if current_group and current_marker == marker:
                prev_node = current_group[-1]
                if self._has_blank_line_between(prev_node, node):
                    groups.append(current_group)
                    current_group = [node]
                    current_marker = marker
                else:
                    current_group.append(node)
            else:
                # Start new group (different marker or first node)
                if current_group:
                    groups.append(current_group)
                current_group = [node]
                current_marker = marker

        # Don't forget the last group
        if current_group:
            groups.append(current_group)

        return groups


__all__ = ["RustCommentAnalyzer"]

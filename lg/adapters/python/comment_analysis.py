"""
Python-specific comment analyzer with docstring support.
"""

from __future__ import annotations

import re
from typing import Optional

from tree_sitter import Node

from ..optimizations.comments import CommentAnalyzer, TruncationStyle, extract_sentence


class PythonCommentAnalyzer(CommentAnalyzer):
    """Python-specific comment analyzer with docstring support."""

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Determine if a comment is a documentation comment in Python.

        Uses two strategies:
        1. capture_name == "docstring" (from Tree-sitter query)
        2. Position-based: string node that is sole child of expression_statement

        Args:
            node: AST node representing the comment
            text: Comment text content
            capture_name: Capture name from Tree-sitter query (optional)

        Returns:
            True if the comment is a documentation comment, False otherwise
        """
        # Strategy 1: Tree-sitter capture name
        if capture_name == "docstring":
            return True

        # Strategy 2: Position-based check
        # In Python, a docstring is a string that is the sole content
        # of an expression_statement
        return self._is_docstring_by_position(node)

    def _is_docstring_by_position(self, node: Node) -> bool:
        """
        Check if node is a docstring based on AST position.

        Args:
            node: AST node to check

        Returns:
            True if node is a docstring, False otherwise
        """
        parent = node.parent
        if parent and parent.type == "expression_statement":
            # If expression_statement contains only one child (this string), it's a docstring
            if len(parent.children) == 1:
                return True
        return False

    def extract_first_sentence(self, text: str) -> str:
        """
        Extract first sentence from Python docstring or comment.

        Args:
            text: Comment text to process

        Returns:
            First sentence with appropriate punctuation and formatting
        """
        # Handle Python docstrings (triple quotes)
        if text.startswith('"""'):
            return self._extract_first_sentence_docstring(text, '"""')
        elif text.startswith("'''"):
            return self._extract_first_sentence_docstring(text, "'''")

        # Handle single-line comments
        elif text.startswith('#'):
            clean_text = text[1:].strip()
            first = extract_sentence(clean_text)
            return f"# {first}."

        # Fallback
        return text

    def _extract_first_sentence_docstring(self, text: str, quote: str) -> str:
        """
        Extract first sentence from triple-quoted docstring.

        Args:
            text: Docstring text to process
            quote: Quote marker (triple double or single quotes)

        Returns:
            First sentence with proper formatting
        """
        # Extract content between triple quotes
        pattern = rf'{re.escape(quote)}\s*(.*?)\s*{re.escape(quote)}'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            content = text[3:].strip()

        first = extract_sentence(content)
        return f'{quote}{first}.{quote}'

    def _detect_truncation_style(self, text: str) -> Optional[TruncationStyle]:
        """
        Detect Python-specific comment style for truncation.
        """
        # Python docstring (triple double quotes)
        if text.startswith('"""'):
            return TruncationStyle(
                start_marker='"""',
                end_marker='"""',
                is_multiline='\n' in text
            )

        # Python docstring (triple single quotes)
        if text.startswith("'''"):
            return TruncationStyle(
                start_marker="'''",
                end_marker="'''",
                is_multiline='\n' in text
            )

        # Hash comments
        if text.startswith('#'):
            return TruncationStyle(
                start_marker='#',
                end_marker='',
                is_multiline=False
            )

        return None  # Unknown style


__all__ = ["PythonCommentAnalyzer"]

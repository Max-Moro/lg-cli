"""
Comment analysis infrastructure for language-specific comment processing.
Provides base classes and utilities for analyzing and processing comments.
"""

from __future__ import annotations

import re
from typing import List, Optional

from tree_sitter import Node

from ..comment_style import CommentStyle
from ..tree_sitter_support import TreeSitterDocument


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

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Determine if a comment is a documentation comment.

        Uses multiple strategies:
        1. Check if capture_name from Tree-sitter query is "docstring"
        2. Check if text starts with documentation markers (e.g., "/**")

        Can be overridden for language-specific logic (e.g., Go position-based detection).

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

        # Strategy 2: Text-based check using doc markers
        stripped = text.strip()
        doc_start, doc_end = self.style.doc_markers
        if doc_start and stripped.startswith(doc_start):
            return True

        return False

    def get_comment_group(self, node: Node) -> Optional[List[Node]]:
        """
        Get group of consecutive comments that form a single documentation block.

        Default returns None (no grouping). Override for languages like Go
        where multiple // comments form one doc block.

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
        # Handle JSDoc comments (/** ... */) with proper indentation
        if text.strip().startswith('/**'):
            # Extract the original indentation by looking at the first line
            lines = text.split('\n')
            if len(lines) > 1:
                # Get indentation from the second line (first content line)
                second_line = lines[1] if len(lines) > 1 else ''
                indent_match = re.match(r'^(\s*)\*', second_line)
                base_indent = indent_match.group(1) if indent_match else '     '
            else:
                base_indent = '     '  # Default JSDoc indentation

            # Extract content between /** and */
            match = re.match(r'/\*\*\s*(.*?)\s*\*/', text, re.DOTALL)
            if match:
                content = match.group(1)
                # Remove leading * from each line
                lines = content.split('\n')
                clean_lines = []
                for line in lines:
                    clean_line = re.sub(r'^\s*\*\s?', '', line)
                    if clean_line.strip():
                        clean_lines.append(clean_line)

                if clean_lines:
                    # Find first sentence in the cleaned content
                    full_text = ' '.join(clean_lines)
                    sentences = re.split(r'[.!?]+', full_text)
                    if sentences and sentences[0].strip():
                        first = sentences[0].strip()
                        # Return with proper JSDoc formatting and indentation
                        return f'/**\n{base_indent}* {first}.\n{base_indent}*/'

            return text  # Fallback if parsing fails

        # Handle regular single-line comments
        elif text.startswith('//'):
            # Remove comment markers and find first sentence
            clean_text = text[2:].strip()
            sentences = re.split(r'[.!?]+', clean_text)
            if sentences and sentences[0].strip():
                first = sentences[0].strip()
                return f"// {first}."

        # Handle regular multiline comments (/* ... */)
        elif text.startswith('/*') and text.rstrip().endswith('*/'):
            # Extract content between /* and */
            match = re.match(r'/\*\s*(.*?)\s*\*/', text, re.DOTALL)
            if match:
                content = match.group(1)
                sentences = re.split(r'[.!?]+', content)
                if sentences and sentences[0].strip():
                    first = sentences[0].strip()
                    return f"/* {first}. */"

        return text  # Fallback to original text

    def truncate_comment(self, text: str, max_tokens: int, tokenizer) -> str:
        """
        Truncate comment while preserving proper closing tags.

        Intelligently truncates comments based on token budget while maintaining
        syntactically correct closing markers.

        Can be overridden for language-specific comment formats.

        Args:
            text: Comment text to truncate
            max_tokens: Maximum allowed tokens
            tokenizer: TokenService for counting and truncating tokens

        Returns:
            Properly truncated comment with correct closing tags
        """
        if tokenizer.count_text_cached(text) <= max_tokens:
            return text

        # JSDoc/TypeScript style comments (/** ... */)
        if text.strip().startswith('/**'):
            # Preserve indentation from original
            lines = text.split('\n')
            if len(lines) > 1:
                second_line = lines[1] if len(lines) > 1 else ''
                indent_match = re.match(r'^(\s*)\*', second_line)
                base_indent = indent_match.group(1) if indent_match else '     '
            else:
                base_indent = '     '

            # Reserve space for closing with proper indentation
            closing = f'\n{base_indent}*/'
            closing_tokens = tokenizer.count_text_cached(closing)
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - closing_tokens - ellipsis_tokens)

            if content_budget < 1:
                return f"/**\n{base_indent}* …\n{base_indent}*/"

            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(text, content_budget)
            return f"{truncated}…{closing}"

        # Regular multiline comment (/* … */)
        elif text.startswith('/*') and text.rstrip().endswith('*/'):
            # Reserve space for ' … */'
            closing = ' … */'
            closing_tokens = tokenizer.count_text_cached(closing)
            content_budget = max(1, max_tokens - closing_tokens)

            if content_budget < 1:
                return "/* … */"

            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(text, content_budget)
            return f"{truncated} … */"

        # Single line comments
        elif text.startswith('//'):
            # Simple truncation with ellipsis
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - ellipsis_tokens)

            if content_budget < 1:
                return f"//…"

            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(text, content_budget)
            return f"{truncated}…"

        # Fallback: simple truncation
        else:
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - ellipsis_tokens)

            if content_budget < 1:
                return "…"

            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(text, content_budget)
            return f"{truncated}…"


__all__ = ["CommentAnalyzer"]

"""
Lexical analyzer for HTML comments with LG instructions.

Detects and extracts special HTML comments containing
conditional logic for the Markdown adapter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class CommentToken:
    """
    HTML comment token with LG instruction.

    Represents special comment with its type and content specification.
    """
    type: str  # 'if', 'elif', 'else', 'endif', 'comment:start', 'comment:end'
    content: str  # Comment content (e.g., condition for if/elif)
    start_pos: int  # Start position in source text
    end_pos: int   # End position in source text
    full_match: str  # Full comment text


class MarkdownTemplateLexer:
    """
    Lexer for finding and extracting LG instructions from HTML comments in Markdown.

    Recognizes following constructs:
    - <!-- lg:if condition -->
    - <!-- lg:elif condition -->
    - <!-- lg:else -->
    - <!-- lg:endif -->
    - <!-- lg:comment:start -->
    - <!-- lg:comment:end -->
    - <!-- lg:raw:start -->
    - <!-- lg:raw:end -->
    """

    # Regular expression for finding LG comments
    LG_COMMENT_PATTERN = re.compile(
        r'<!--\s*lg:([a-z:]+)(?:\s+([^-]+(?:-(?!->)[^-]*)*))?\s*-->',
        re.MULTILINE
    )

    def __init__(self, text: str):
        """
        Initialize lexer with source text.

        Args:
            text: Source Markdown text for analysis
        """
        self.text = text
        self.length = len(text)
    
    def tokenize(self) -> List[CommentToken]:
        """
        Extracts all LG comments from text.

        Returns:
            List of comment tokens sorted by position in text
        """
        tokens = []

        for match in self.LG_COMMENT_PATTERN.finditer(self.text):
            token_type = match.group(1)  # Instruction type (if, elif, else, etc.)
            content = match.group(2) or ""  # Content (condition for if/elif)
            start_pos = match.start()
            end_pos = match.end()
            full_match = match.group(0)

            # Clean content of extra spaces
            content = content.strip()

            # Validate token type
            if not self._is_valid_token_type(token_type):
                # Ignore unknown comment types
                continue

            token = CommentToken(
                type=token_type,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos,
                full_match=full_match
            )

            tokens.append(token)

        # Sort tokens by position in text
        tokens.sort(key=lambda t: t.start_pos)

        return tokens
    
    def find_text_segments(self, tokens: List[CommentToken]) -> List[Tuple[int, int, str]]:
        """
        Split text into segments between LG comments.

        Args:
            tokens: List of comment tokens

        Returns:
            List of tuples (start_pos, end_pos, segment_type),
            where segment_type can be 'text' or 'comment'
        """
        segments = []
        current_pos = 0

        for token in tokens:
            # Add text segment before comment
            if current_pos < token.start_pos:
                segments.append((current_pos, token.start_pos, 'text'))

            # Add comment itself
            segments.append((token.start_pos, token.end_pos, 'comment'))

            current_pos = token.end_pos

        # Add remaining text after last comment
        if current_pos < self.length:
            segments.append((current_pos, self.length, 'text'))

        return segments
    
    def extract_text_between(self, start_token: CommentToken, end_token: CommentToken) -> str:
        """
        Extract text between two comment tokens.

        Args:
            start_token: Start token (e.g., lg:if)
            end_token: End token (e.g., lg:endif)

        Returns:
            Text between tokens
        """
        if start_token.end_pos >= end_token.start_pos:
            return ""

        return self.text[start_token.end_pos:end_token.start_pos]
    
    def _is_valid_token_type(self, token_type: str) -> bool:
        """
        Check if token type is valid.

        Args:
            token_type: Token type to check

        Returns:
            True if token type is supported
        """
        valid_types = {
            'if',
            'elif',
            'else',
            'endif',
            'comment:start',
            'comment:end',
            'raw:start',
            'raw:end'
        }

        return token_type in valid_types
    
    def validate_tokens(self, tokens: List[CommentToken]) -> List[str]:
        """
        Validate token sequence for structure correctness.

        Args:
            tokens: List of tokens to validate

        Returns:
            List of validation errors (empty if no errors)
        """
        errors = []
        stack = []  # Stack for tracking open blocks
        comment_blocks = 0  # Counter of open comment blocks

        for i, token in enumerate(tokens):
            if token.type == 'if':
                if not token.content:
                    errors.append(f"Token {i}: 'if' without condition at position {token.start_pos}")
                stack.append(('if', i))

            elif token.type == 'elif':
                if not token.content:
                    errors.append(f"Token {i}: 'elif' without condition at position {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif'):
                    errors.append(f"Token {i}: 'elif' without matching 'if' at position {token.start_pos}")
                else:
                    # Replace last stack element with elif
                    stack[-1] = ('elif', i)

            elif token.type == 'else':
                if token.content:
                    errors.append(f"Token {i}: 'else' should not have condition at position {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif'):
                    errors.append(f"Token {i}: 'else' without matching 'if' at position {token.start_pos}")
                else:
                    # Replace last stack element with else
                    stack[-1] = ('else', i)

            elif token.type == 'endif':
                if token.content:
                    errors.append(f"Token {i}: 'endif' should not have condition at position {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif', 'else'):
                    errors.append(f"Token {i}: 'endif' without matching 'if' at position {token.start_pos}")
                else:
                    stack.pop()

            elif token.type == 'comment:start':
                if token.content:
                    errors.append(f"Token {i}: 'comment:start' should not have content at position {token.start_pos}")
                comment_blocks += 1

            elif token.type == 'comment:end':
                if token.content:
                    errors.append(f"Token {i}: 'comment:end' should not have content at position {token.start_pos}")
                comment_blocks -= 1
                if comment_blocks < 0:
                    errors.append(f"Token {i}: 'comment:end' without matching 'comment:start' at position {token.start_pos}")

            elif token.type == 'raw:start':
                if token.content:
                    errors.append(f"Token {i}: 'raw:start' should not have content at position {token.start_pos}")
                stack.append(('raw', i))

            elif token.type == 'raw:end':
                if token.content:
                    errors.append(f"Token {i}: 'raw:end' should not have content at position {token.start_pos}")
                if not stack or stack[-1][0] != 'raw':
                    errors.append(f"Token {i}: 'raw:end' without matching 'raw:start' at position {token.start_pos}")
                else:
                    stack.pop()

        # Check remaining open blocks
        for block_type, token_index in stack:
            errors.append(f"Token {token_index}: Unclosed block '{block_type}'")

        if comment_blocks > 0:
            errors.append(f"Unclosed 'comment' blocks: {comment_blocks}")

        return errors


def tokenize_markdown_template(text: str) -> List[CommentToken]:
    """
    Convenience function for tokenizing Markdown with LG comments.

    Args:
        text: Source Markdown text

    Returns:
        List of comment tokens
    """
    lexer = MarkdownTemplateLexer(text)
    return lexer.tokenize()


__all__ = [
    "CommentToken",
    "MarkdownTemplateLexer", 
    "tokenize_markdown_template"
]
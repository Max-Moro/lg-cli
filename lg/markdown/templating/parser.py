"""
Parser for conditional constructs in Markdown.

Transforms HTML comment tokens into AST with support for
conditional blocks and instruction comments.
"""

from __future__ import annotations

from typing import List, Optional

from .lexer import CommentToken, MarkdownTemplateLexer
from .nodes import (
    MarkdownAST, MarkdownNode, TextNode, ConditionalBlockNode,
    ElifBlockNode, ElseBlockNode, CommentBlockNode, RawBlockNode
)
from ...errors import LGUserError


class MarkdownTemplateParserError(LGUserError):
    """Error in parsing Markdown with conditional constructs."""

    def __init__(self, message: str, token: Optional[CommentToken] = None):
        if token:
            super().__init__(f"{message} in token '{token.type}' at position {token.start_pos}")
        else:
            super().__init__(message)
        self.token = token


class MarkdownTemplateParser:
    """
    Parser for Markdown with conditional constructs in HTML comments.

    Transforms sequence of comment tokens and text segments
    into AST, correctly handling nested conditional constructs.
    """

    def __init__(self, text: str):
        """
        Initialize parser with source text.

        Args:
            text: Source Markdown text for parsing
        """
        self.text = text
        self.lexer = MarkdownTemplateLexer(text)
        
    def parse(self) -> MarkdownAST:
        """
        Parse text into AST.

        Returns:
            AST with conditional constructs

        Raises:
            MarkdownTemplateParserError: On parsing error
        """
        # Get comment tokens
        tokens = self.lexer.tokenize()

        # Validate token structure
        validation_errors = self.lexer.validate_tokens(tokens)
        if validation_errors:
            raise MarkdownTemplateParserError(
                f"Structure validation errors: {'; '.join(validation_errors)}"
            )

        # If no tokens, return simple text node
        if not tokens:
            return [TextNode(text=self.text)]

        # Parse considering tokens
        return self._parse_with_tokens(tokens)
    
    def _parse_with_tokens(self, tokens: List[CommentToken]) -> MarkdownAST:
        """
        Parse text considering found comment tokens.

        Args:
            tokens: List of comment tokens

        Returns:
            List of AST nodes
        """
        ast = []
        current_pos = 0
        token_index = 0
        
        while token_index < len(tokens):
            token = tokens[token_index]

            # Add text before token
            if current_pos < token.start_pos:
                text_content = self.text[current_pos:token.start_pos]
                if text_content:
                    ast.append(TextNode(text=text_content))
            
            # Process token
            if token.type == 'if':
                # Parse conditional block
                if_block, consumed_tokens = self._parse_conditional_block(tokens, token_index)
                ast.append(if_block)
                token_index += consumed_tokens
                # Update position to end of last processed token
                if token_index < len(tokens):
                    current_pos = tokens[token_index - 1].end_pos
                else:
                    current_pos = tokens[-1].end_pos

            elif token.type == 'comment:start':
                # Parse comment block
                comment_block, consumed_tokens = self._parse_comment_block(tokens, token_index)
                ast.append(comment_block)
                token_index += consumed_tokens
                # Update position to end of last processed token
                if token_index < len(tokens):
                    current_pos = tokens[token_index - 1].end_pos
                else:
                    current_pos = tokens[-1].end_pos

            elif token.type == 'raw:start':
                # Parse raw block
                raw_block, consumed_tokens = self._parse_raw_block(tokens, token_index)
                ast.append(raw_block)
                token_index += consumed_tokens
                # Update position to end of last processed token
                if token_index < len(tokens):
                    current_pos = tokens[token_index - 1].end_pos
                else:
                    current_pos = tokens[-1].end_pos

            else:
                # Unexpected token at top level
                raise MarkdownTemplateParserError(
                    f"Unexpected token '{token.type}' at top level", token
                )
        
        # Add remaining text
        if current_pos < len(self.text):
            remaining_text = self.text[current_pos:]
            if remaining_text:
                ast.append(TextNode(text=remaining_text))

        return ast
    
    def _parse_conditional_block(self, tokens: List[CommentToken], start_index: int) -> tuple[ConditionalBlockNode, int]:
        """
        Parse conditional block if...elif...else...endif.

        Args:
            tokens: List of all tokens
            start_index: Index of 'if' token

        Returns:
            Tuple (conditional block node, number of processed tokens)
        """
        if_token = tokens[start_index]
        if if_token.type != 'if':
            raise MarkdownTemplateParserError("Expected 'if' token", if_token)

        # Find matching endif
        endif_index = self._find_matching_endif(tokens, start_index)
        if endif_index == -1:
            raise MarkdownTemplateParserError("Matching 'endif' not found", if_token)
        
        # Parse conditional block content
        condition_text = if_token.content

        # Find elif and else tokens within block
        elif_indices = []
        else_index = -1

        for i in range(start_index + 1, endif_index):
            token = tokens[i]
            if token.type == 'elif' and self._is_at_same_level(tokens, start_index, i):
                elif_indices.append(i)
            elif token.type == 'else' and self._is_at_same_level(tokens, start_index, i):
                if else_index != -1:
                    raise MarkdownTemplateParserError("Multiple 'else' in one block", token)
                else_index = i
        
        # Check elif and else order
        if else_index != -1 and elif_indices:
            if any(ei > else_index for ei in elif_indices):
                else_token = tokens[else_index]
                raise MarkdownTemplateParserError("'elif' after 'else'", else_token)

        # Parse if block body
        body_start = if_token.end_pos
        body_end = tokens[elif_indices[0]].start_pos if elif_indices else (
            tokens[else_index].start_pos if else_index != -1 else tokens[endif_index].start_pos
        )

        if_body = self._parse_body_between_positions(tokens, start_index + 1, body_start, body_end)

        # Parse elif blocks
        elif_blocks = []
        for i, elif_idx in enumerate(elif_indices):
            elif_token = tokens[elif_idx]
            elif_body_start = elif_token.end_pos

            # Determine end of elif block body
            next_idx = elif_indices[i + 1] if i + 1 < len(elif_indices) else (
                else_index if else_index != -1 else endif_index
            )
            elif_body_end = tokens[next_idx].start_pos

            elif_body = self._parse_body_between_positions(tokens, elif_idx + 1, elif_body_start, elif_body_end)

            elif_blocks.append(ElifBlockNode(
                condition_text=elif_token.content,
                body=elif_body
            ))

        # Parse else block
        else_block = None
        if else_index != -1:
            else_token = tokens[else_index]
            else_body_start = else_token.end_pos
            else_body_end = tokens[endif_index].start_pos

            else_body = self._parse_body_between_positions(tokens, else_index + 1, else_body_start, else_body_end)
            else_block = ElseBlockNode(body=else_body)
        
        conditional_block = ConditionalBlockNode(
            condition_text=condition_text,
            body=if_body,
            elif_blocks=elif_blocks,
            else_block=else_block
        )

        # Return node and number of processed tokens
        consumed_tokens = endif_index - start_index + 1
        return conditional_block, consumed_tokens
    
    def _parse_comment_block(self, tokens: List[CommentToken], start_index: int) -> tuple[CommentBlockNode, int]:
        """
        Parse comment block comment:start...comment:end.

        Args:
            tokens: List of all tokens
            start_index: Index of 'comment:start' token

        Returns:
            Tuple (comment node, number of processed tokens)
        """
        start_token = tokens[start_index]
        if start_token.type != 'comment:start':
            raise MarkdownTemplateParserError("Expected 'comment:start' token", start_token)

        # Find matching comment:end
        end_index = -1
        for i in range(start_index + 1, len(tokens)):
            if tokens[i].type == 'comment:end':
                end_index = i
                break

        if end_index == -1:
            raise MarkdownTemplateParserError("Matching 'comment:end' not found", start_token)

        # Extract comment text
        comment_start = start_token.end_pos
        comment_end = tokens[end_index].start_pos
        comment_text = self.text[comment_start:comment_end]

        comment_block = CommentBlockNode(text=comment_text)

        consumed_tokens = end_index - start_index + 1
        return comment_block, consumed_tokens
    
    def _parse_raw_block(self, tokens: List[CommentToken], start_index: int) -> tuple[RawBlockNode, int]:
        """
        Parse raw text block raw:start...raw:end.

        Args:
            tokens: List of all tokens
            start_index: Index of 'raw:start' token

        Returns:
            Tuple (raw block node, number of processed tokens)
        """
        start_token = tokens[start_index]
        if start_token.type != 'raw:start':
            raise MarkdownTemplateParserError("Expected 'raw:start' token", start_token)

        # Find matching raw:end considering nesting
        end_index = -1
        nesting_level = 1

        for i in range(start_index + 1, len(tokens)):
            if tokens[i].type == 'raw:start':
                nesting_level += 1
            elif tokens[i].type == 'raw:end':
                nesting_level -= 1
                if nesting_level == 0:
                    end_index = i
                    break

        if end_index == -1:
            raise MarkdownTemplateParserError("Matching 'raw:end' not found", start_token)

        # Extract raw block text WITHOUT processing (as-is)
        raw_start = start_token.end_pos
        raw_end = tokens[end_index].start_pos
        raw_text = self.text[raw_start:raw_end]

        raw_block = RawBlockNode(text=raw_text)

        consumed_tokens = end_index - start_index + 1
        return raw_block, consumed_tokens
    
    def _parse_body_between_positions(self, all_tokens: List[CommentToken],
                                    _start_token_index: int, start_pos: int, end_pos: int) -> List[MarkdownNode]:
        """
        Parse body between specified positions in text.

        Args:
            all_tokens: All document tokens
            start_token_index: Start token index (for determining nesting level)
            start_pos: Start position in text
            end_pos: End position in text

        Returns:
            List of nodes for body
        """
        # Filter tokens that fall in range
        relevant_tokens = [
            token for token in all_tokens
            if start_pos <= token.start_pos < end_pos
        ]

        if not relevant_tokens:
            # If no tokens in range, return just text
            body_text = self.text[start_pos:end_pos]
            return [TextNode(text=body_text)] if body_text else []

        # Create temporary parser for this fragment
        body_text = self.text[start_pos:end_pos]

        # Adjust token positions relative to fragment start
        adjusted_tokens = []
        for token in relevant_tokens:
            adjusted_token = CommentToken(
                type=token.type,
                content=token.content,
                start_pos=token.start_pos - start_pos,
                end_pos=token.end_pos - start_pos,
                full_match=token.full_match
            )
            adjusted_tokens.append(adjusted_token)

        # Create temporary parser
        temp_parser = MarkdownTemplateParser(body_text)
        return temp_parser._parse_with_tokens(adjusted_tokens)
    
    def _find_matching_endif(self, tokens: List[CommentToken], if_index: int) -> int:
        """
        Find matching endif for if token.

        Args:
            tokens: List of tokens
            if_index: Index of if token

        Returns:
            Index of matching endif or -1 if not found
        """
        if_count = 1  # Start with 1 for current if

        for i in range(if_index + 1, len(tokens)):
            token = tokens[i]
            if token.type == 'if':
                if_count += 1
            elif token.type == 'endif':
                if_count -= 1
                if if_count == 0:
                    return i

        return -1
    
    def _is_at_same_level(self, tokens: List[CommentToken], if_index: int, target_index: int) -> bool:
        """
        Check if token is at same nesting level as if.

        Args:
            tokens: List of tokens
            if_index: Index of if token
            target_index: Index of token to check

        Returns:
            True if tokens are at same level
        """
        if_count = 1  # Start with 1 for original if

        for i in range(if_index + 1, target_index):
            token = tokens[i]
            if token.type == 'if':
                if_count += 1
            elif token.type == 'endif':
                if_count -= 1

        return if_count == 1


def parse_markdown_template(text: str) -> MarkdownAST:
    """
    Convenience function for parsing Markdown with conditional constructs.

    Args:
        text: Source Markdown text

    Returns:
        AST with conditional constructs

    Raises:
        MarkdownTemplateParserError: On parsing error
    """
    parser = MarkdownTemplateParser(text)
    return parser.parse()


__all__ = [
    "MarkdownTemplateParser",
    "MarkdownTemplateParserError",
    "parse_markdown_template"
]
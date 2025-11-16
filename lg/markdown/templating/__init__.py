"""
Package for processing conditional constructs in Markdown.

Provides AST-based approach for processing LG instructions
in HTML comments inside Markdown documents.
"""

from .processor import process_markdown_template, MarkdownTemplateProcessorError
from .parser import parse_markdown_template, MarkdownTemplateParserError
from .lexer import tokenize_markdown_template, CommentToken

__all__ = [
    # Main function for use
    "process_markdown_template",

    # Exceptions
    "MarkdownTemplateProcessorError",
    "MarkdownTemplateParserError",

    # Low-level functions (for testing and debugging)
    "parse_markdown_template",
    "tokenize_markdown_template",
]
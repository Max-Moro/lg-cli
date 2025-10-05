"""
Пакет для обработки условных конструкций в Markdown.

Предоставляет AST-based подход для обработки LG-инструкций
в HTML-комментариях внутри Markdown-документов.
"""

from .processor import process_markdown_template, MarkdownTemplateProcessorError
from .parser import parse_markdown_template, MarkdownTemplateParserError
from .lexer import tokenize_markdown_template, CommentToken

__all__ = [
    # Основная функция для использования
    "process_markdown_template",
    
    # Исключения
    "MarkdownTemplateProcessorError",
    "MarkdownTemplateParserError",
    
    # Низкоуровневые функции (для тестирования и отладки)
    "parse_markdown_template",
    "tokenize_markdown_template",
]
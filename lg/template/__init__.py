from __future__ import annotations

from .processor import TemplateProcessor, create_template_processor, TemplateProcessingError
from .context import TemplateContext, create_template_context
from .nodes import (
    TemplateNode, TemplateAST, TextNode, SectionNode, IncludeNode, 
    ConditionalBlockNode, ModeBlockNode, CommentNode, ElseBlockNode
)
from .lexer import TemplateLexer, tokenize_template, LexerError
from .parser import TemplateParser, parse_template, ParserError
from .evaluator import TemplateConditionEvaluator, evaluate_simple_condition

__all__ = [
    # Основной API
    "TemplateProcessor",
    "create_template_processor",
    "TemplateProcessingError",
    
    # Контекст
    "TemplateContext", 
    "create_template_context",
    
    # AST узлы
    "TemplateNode",
    "TemplateAST",
    "TextNode", 
    "SectionNode",
    "IncludeNode",
    "ConditionalBlockNode", 
    "ModeBlockNode",
    "CommentNode",
    "ElseBlockNode",
    
    # Низкоуровневые компоненты
    "TemplateLexer",
    "tokenize_template",
    "LexerError",
    "TemplateParser", 
    "parse_template",
    "ParserError",
    "TemplateConditionEvaluator",
    "evaluate_simple_condition",
]
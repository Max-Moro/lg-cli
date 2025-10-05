"""
AST-узлы для условной логики в Markdown.

Определяет иерархию узлов для представления условных конструкций
в HTML-комментариях внутри Markdown-документов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MarkdownNode:
    """Базовый класс для всех узлов AST Markdown с условной логикой."""
    pass


@dataclass(frozen=True)
class TextNode(MarkdownNode):
    """
    Обычный текстовый контент в Markdown.
    
    Представляет статический текст, который не требует обработки
    и выводится в результат как есть.
    """
    text: str


@dataclass(frozen=True)
class ConditionalBlockNode(MarkdownNode):
    """
    Условный блок <!-- lg:if condition -->...<!-- lg:endif -->.
    
    Представляет условную конструкцию в HTML-комментариях, которая 
    включает или исключает содержимое на основе вычисления условного 
    выражения с поддержкой цепочек elif блоков.
    """
    condition_text: str  # Исходный текст условия
    body: List[MarkdownNode]
    elif_blocks: Optional[List[ElifBlockNode]] = None
    else_block: Optional[ElseBlockNode] = None
    
    def __post_init__(self):
        if self.elif_blocks is None:
            object.__setattr__(self, 'elif_blocks', [])


@dataclass(frozen=True)
class ElifBlockNode(MarkdownNode):
    """
    Блок <!-- lg:elif condition --> внутри условных конструкций.
    
    Представляет условное альтернативное содержимое, которое проверяется
    если предыдущие условия в цепочке if/elif не выполнились.
    """
    condition_text: str  # Исходный текст условия
    body: List[MarkdownNode]


@dataclass(frozen=True)
class ElseBlockNode(MarkdownNode):
    """
    Блок <!-- lg:else --> внутри условных конструкций.
    
    Представляет альтернативное содержимое, которое используется
    если условие в ConditionalBlockNode не выполняется.
    """
    body: List[MarkdownNode]


@dataclass(frozen=True)
class CommentBlockNode(MarkdownNode):
    """
    Блок комментария <!-- lg:comment:start -->...<!-- lg:comment:end -->.
    
    Представляет комментарий в Markdown, который должен быть удален
    при обработке LG, но остается видимым в обычных Markdown-просмотрщиках.
    """
    text: str


@dataclass(frozen=True)
class RawBlockNode(MarkdownNode):
    """
    Блок raw-текста <!-- lg:raw:start -->...<!-- lg:raw:end -->.
    
    Представляет блок текста, который должен быть выведен как есть,
    без обработки вложенных LG-инструкций. Все HTML-комментарии внутри
    такого блока сохраняются в итоговом выводе.
    """
    text: str


# Тип для коллекции узлов Markdown
MarkdownAST = List[MarkdownNode]


def collect_text_content(ast: MarkdownAST) -> str:
    """
    Собирает весь текстовый контент из AST (для тестирования и отладки).
    
    Args:
        ast: AST для обработки
        
    Returns:
        Объединенный текстовый контент
    """
    result_parts = []
    
    def collect_from_node(node: MarkdownNode) -> None:
        if isinstance(node, TextNode):
            result_parts.append(node.text)
        elif isinstance(node, ConditionalBlockNode):
            for child in node.body:
                collect_from_node(child)
            if node.elif_blocks:
                for elif_block in node.elif_blocks:
                    collect_from_node(elif_block)
            if node.else_block:
                collect_from_node(node.else_block)
        elif isinstance(node, (ElifBlockNode, ElseBlockNode)):
            for child in node.body:
                collect_from_node(child)
        elif isinstance(node, CommentBlockNode):
            # Комментарии не включаются в текстовый контент
            pass
        elif isinstance(node, RawBlockNode):
            # Raw-блоки выводятся как есть
            result_parts.append(node.text)
    
    for node in ast:
        collect_from_node(node)
    
    return "".join(result_parts)


def format_ast_tree(ast: MarkdownAST, indent: int = 0) -> str:
    """Форматирует AST как дерево для отладки."""
    lines = []
    prefix = "  " * indent
    
    for node in ast:
        if isinstance(node, TextNode):
            # Показываем только начало текста для читабельности
            text_preview = repr(node.text[:50] + "..." if len(node.text) > 50 else node.text)
            lines.append(f"{prefix}TextNode({text_preview})")
        elif isinstance(node, ConditionalBlockNode):
            lines.append(f"{prefix}ConditionalBlockNode(condition='{node.condition_text}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
            if node.elif_blocks:
                for i, elif_block in enumerate(node.elif_blocks):
                    lines.append(f"{prefix}  elif[{i}]:")
                    lines.append(format_ast_tree([elif_block], indent + 2))
            if node.else_block:
                lines.append(f"{prefix}  else:")
                lines.append(format_ast_tree([node.else_block], indent + 2))
        elif isinstance(node, ElifBlockNode):
            lines.append(f"{prefix}ElifBlockNode(condition='{node.condition_text}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
        elif isinstance(node, ElseBlockNode):
            lines.append(f"{prefix}ElseBlockNode")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
        elif isinstance(node, CommentBlockNode):
            comment_preview = repr(node.text[:30] + "..." if len(node.text) > 30 else node.text)
            lines.append(f"{prefix}CommentBlockNode({comment_preview})")
        elif isinstance(node, RawBlockNode):
            raw_preview = repr(node.text[:30] + "..." if len(node.text) > 30 else node.text)
            lines.append(f"{prefix}RawBlockNode({raw_preview})")
        else:
            lines.append(f"{prefix}{type(node).__name__}")
    
    return "\n".join(lines)


__all__ = [
    "MarkdownNode",
    "MarkdownAST", 
    "TextNode",
    "ConditionalBlockNode",
    "ElifBlockNode", 
    "ElseBlockNode",
    "CommentBlockNode",
    "RawBlockNode",
    "collect_text_content",
    "format_ast_tree"
]
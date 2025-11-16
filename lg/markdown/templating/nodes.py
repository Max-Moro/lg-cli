"""
AST nodes for conditional logic in Markdown.

Defines node hierarchy for representing conditional constructs
in HTML comments inside Markdown documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MarkdownNode:
    """Base class for all AST nodes in Markdown with conditional logic."""
    pass


@dataclass(frozen=True)
class TextNode(MarkdownNode):
    """
    Regular text content in Markdown.

    Represents static text that doesn't require processing
    and is output as-is in the result.
    """
    text: str


@dataclass(frozen=True)
class ConditionalBlockNode(MarkdownNode):
    """
    Conditional block <!-- lg:if condition -->...<!-- lg:endif -->.

    Represents conditional construct in HTML comments that
    includes or excludes content based on condition evaluation
    with support for elif block chains.
    """
    condition_text: str  # Original condition text
    body: List[MarkdownNode]
    elif_blocks: Optional[List[ElifBlockNode]] = None
    else_block: Optional[ElseBlockNode] = None

    def __post_init__(self):
        if self.elif_blocks is None:
            object.__setattr__(self, 'elif_blocks', [])


@dataclass(frozen=True)
class ElifBlockNode(MarkdownNode):
    """
    Block <!-- lg:elif condition --> within conditional constructs.

    Represents alternative content that is checked
    if previous conditions in the if/elif chain didn't succeed.
    """
    condition_text: str  # Original condition text
    body: List[MarkdownNode]


@dataclass(frozen=True)
class ElseBlockNode(MarkdownNode):
    """
    Block <!-- lg:else --> within conditional constructs.

    Represents alternative content used
    if the condition in ConditionalBlockNode is false.
    """
    body: List[MarkdownNode]


@dataclass(frozen=True)
class CommentBlockNode(MarkdownNode):
    """
    Comment block <!-- lg:comment:start -->...<!-- lg:comment:end -->.

    Represents comment in Markdown that should be removed
    during LG processing but remains visible in regular Markdown viewers.
    """
    text: str


@dataclass(frozen=True)
class RawBlockNode(MarkdownNode):
    """
    Raw text block <!-- lg:raw:start -->...<!-- lg:raw:end -->.

    Represents block of text that should be output as-is,
    without processing nested LG instructions. All HTML comments inside
    such blocks are preserved in the final output.
    """
    text: str


# Type for collection of Markdown nodes
MarkdownAST = List[MarkdownNode]


def collect_text_content(ast: MarkdownAST) -> str:
    """
    Collects all text content from AST (for testing and debugging).

    Args:
        ast: AST to process

    Returns:
        Combined text content
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
            # Comments not included in text content
            pass
        elif isinstance(node, RawBlockNode):
            # Raw blocks output as-is
            result_parts.append(node.text)
    
    for node in ast:
        collect_from_node(node)
    
    return "".join(result_parts)


def format_ast_tree(ast: MarkdownAST, indent: int = 0) -> str:
    """Format AST as tree for debugging."""
    lines = []
    prefix = "  " * indent

    for node in ast:
        if isinstance(node, TextNode):
            # Show only beginning of text for readability
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
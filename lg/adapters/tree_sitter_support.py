"""
Tree-sitter infrastructure for language adapters.
Provides grammar loading, query management, and utilities for AST parsing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from tree_sitter import Tree, Node, Language, Parser


class TreeSitterDocument(ABC):
    """Wrapper for Tree-sitter parsed document."""

    def __init__(self, text: str, ext: str):
        self.text = text
        self.ext = ext
        self.tree: Optional[Tree] = None
        self._parse()

    @abstractmethod
    def get_language_parser(self) -> Parser:
        """
        Get cached language and parser for the given language.

        Returns:
            Tuple of (Language, Parser)
        """
        pass

    def _parse(self):
        """Parse the document with Tree-sitter."""
        self.tree = self.get_language_parser().parse(self.text.encode('utf-8'))

    @property
    def root_node(self) -> Node:
        """Get the root node of the parsed tree."""
        if not self.tree:
            raise RuntimeError("Document not parsed")
        return self.tree.root_node

    def query(self, query_name: str) -> List[Tuple[Node, str]]:
        """
        Execute a named query on the document.

        Returns:
            List of (node, capture_name) tuples
        """
        # TODO реализовать через Tree-sitter API для queries
        return []

    def get_node_text(self, node: Node) -> str:
        """Get text content for a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return self.text.encode('utf-8')[start_byte:end_byte].decode('utf-8')

    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """Get byte range for a node."""
        return node.start_byte, node.end_byte

    def get_line_range(self, node: Node) -> Tuple[int, int]:
        """Get line range (0-based) for a node."""
        return node.start_point[0], node.end_point[0]


"""
Tree-sitter infrastructure for language adapters.
Provides grammar loading, query management, and utilities for AST parsing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from tree_sitter import Tree, Node, Parser, Language, QueryCursor, Query


class TreeSitterDocument(ABC):
    """
    Wrapper for Tree-sitter parsed document with query system.
    """

    def __init__(self, text: str, ext: str):
        self.text = text
        self.ext = ext
        self.tree: Optional[Tree] = None
        self._text_bytes = text.encode('utf-8')
        self._query_cache: dict[str, Query] = {}  # Cache for compiled Query objects
        self._parse()

    @abstractmethod
    def get_language(self) -> Language:
        """
        Get Language instance for queries.
        
        Returns:
            Language instance
        """
        pass

    def get_parser(self) -> Parser:
        """
        Get parser for the language.

        Returns:
            Parser instance
        """
        return Parser(self.get_language())

    def _parse(self):
        """Parse the document with Tree-sitter."""
        parser = self.get_parser()
        self.tree = parser.parse(self._text_bytes)

    @property
    def root_node(self) -> Node:
        """Get the root node of the parsed tree."""
        if not self.tree:
            raise RuntimeError("Document not parsed")
        return self.tree.root_node

    def query_nodes(self, query_string: str, capture_name: str) -> List[Node]:
        """
        Execute a Tree-sitter query and return flat list of matching nodes.

        Returns only nodes captured with the specified capture name.
        Other captures are used for predicates but not returned.

        Query objects are cached for performance - repeated calls with
        the same query_string reuse the compiled Query (~100x faster).

        Args:
            query_string: S-expression query string
            capture_name: Name of the capture to return

        Returns:
            List of matching nodes with the specified capture name
        """
        # Cache compiled Query objects for performance
        if query_string not in self._query_cache:
            self._query_cache[query_string] = Query(self.get_language(), query_string)

        query = self._query_cache[query_string]
        cursor = QueryCursor(query)

        nodes = []
        matches = cursor.matches(self.root_node)

        # Use matches to get pattern matches with capture info
        # Only return nodes with the specified capture name
        for pattern_index, captures in matches:
            if capture_name in captures:
                for node in captures[capture_name]:
                    nodes.append(node)

        return nodes

    def walk_tree(self, start_node: Optional[Node] = None):
        """
        Walk the tree using TreeCursor for efficient traversal.
        
        Args:
            start_node: Node to start from (default: root)
            
        Yields:
            Node objects in depth-first order
        """
        if start_node is None:
            start_node = self.root_node
            
        cursor = start_node.walk()
        visited_children = False
        
        while True:
            if not visited_children:
                yield cursor.node
                
                if not cursor.goto_first_child():
                    visited_children = True
            elif cursor.goto_next_sibling():
                visited_children = False
            elif not cursor.goto_parent():
                break
            else:
                visited_children = True

    def get_line_number(self, char_offset: int) -> int:
        """
        Get line number (0-based) for given offset.
        """
        # Simple implementation - count line breaks up to this character position
        text_before = self.text[:char_offset]
        return text_before.count('\n')

    def get_node_text(self, node: Node) -> str:
        """Get text content for a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return self._text_bytes[start_byte:end_byte].decode('utf-8')

    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """Get char range for a node."""
        start_char = self.byte_to_char_position(node.start_byte)
        end_char = self.byte_to_char_position(node.end_byte)
        return start_char, end_char

    @staticmethod
    def get_line_range(node: Node) -> Tuple[int, int]:
        """Get line range (0-based) for a node."""
        return node.start_point[0], node.end_point[0]

    @staticmethod
    def get_parent_of_type(node: Node, node_type: str) -> Optional[Node]:
        """
        Find the first parent of a specific type.
        
        Args:
            node: Starting node
            node_type: Type to search for
            
        Returns:
            Parent node of the specified type, or None
        """
        current = node.parent
        while current:
            if current.type == node_type:
                return current
            current = current.parent
        return None

    @staticmethod
    def get_children_by_type(node: Node, node_type: str) -> List[Node]:
        """
        Get direct children of a specific type.
        
        Args:
            node: Parent node
            node_type: Type to filter by
            
        Returns:
            List of child nodes of the specified type
        """
        return [child for child in node.children if child.type == node_type]

    def has_error(self) -> bool:
        """Check if the tree has any syntax errors."""
        if not self.tree:
            return True
        return self.root_node.has_error

    def get_errors(self) -> List[Node]:
        """Get all error nodes in the tree."""
        return self.query_nodes("(ERROR) @error", "error")

    def byte_to_char_position(self, byte_pos: int) -> int:
        """
        Correctly convert byte position to character position in Unicode text.
        Guarantees that if position points to the middle of a multi-byte character,
        returns position before that character.
        """
        if byte_pos <= 0:
            return 0
        if byte_pos >= len(self._text_bytes):
            # If position is beyond text, return text length in characters
            return len(self.text)

        # Search for longest valid slice
        # (UTF-8 guarantees maximum 4 bytes per character)
        start = max(0, byte_pos - 4)
        for end in range(byte_pos, start - 1, -1):
            try:
                decoded = self._text_bytes[:end].decode('utf-8')
                return len(decoded)
            except UnicodeDecodeError:
                continue
        # If couldn't decode any slice, return 0
        return 0

    def count_removed_lines(self, start_char: int, end_char: int) -> int:
        """
        Count non-empty lines in the text range.

        Args:
            start_char: Start position in characters
            end_char: End position in characters

        Returns:
            Number of non-empty lines in the range
        """
        if start_char >= end_char:
            return 0

        removed_text = self.text[start_char:end_char]
        lines = removed_text.split('\n')
        return sum(1 for line in lines if line.strip())

"""Body range computation for function/method elements."""

from typing import Optional, Set, Tuple, Callable

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument


class BodyRangeComputer:
    """Computes strippable range for function bodies."""

    def __init__(self, doc: TreeSitterDocument, comment_types: Set[str]):
        """
        Initialize body range computer.

        Args:
            doc: Tree-sitter document
            comment_types: Set of comment node types for this language
        """
        self.doc = doc
        self.comment_types = comment_types

    def compute(
        self,
        func_def: Node,
        body_node: Node,
        docstring_extractor: Optional[Callable[[Node, TreeSitterDocument], Optional[Node]]] = None,
        body_range_computer: Optional[Callable[[Node, TreeSitterDocument], Tuple[int, int]]] = None,
    ) -> Tuple[int, int]:
        """
        Compute strippable byte range for function body.

        Handles:
        - Brace-based languages (excludes braces)
        - Leading comments as siblings (Python style)
        - Docstrings (via profile.docstring_extractor)
        - Line-based start (preserving indentation for Python-style languages)
        - Custom body range computation (via profile.body_range_computer)

        Args:
            func_def: Function definition node
            body_node: Body node (block, statement_block, etc.)
            docstring_extractor: Optional callback to find docstring
            body_range_computer: Optional custom range computer from profile

        Returns:
            Tuple of (start_byte, end_byte) for strippable content
        """
        # Custom computer takes precedence
        if body_range_computer:
            return body_range_computer(func_def, self.doc)

        # Standard computation
        start_byte, end_byte = self._compute_inner_range(body_node)
        is_brace_based = (start_byte != body_node.start_byte)

        # Check for leading sibling comments
        sibling_comment_start = self._find_leading_sibling_comments(func_def, body_node)
        if sibling_comment_start is not None:
            start_byte = min(start_byte, sibling_comment_start)

        # Adjust for docstring
        if docstring_extractor:
            docstring = docstring_extractor(body_node, self.doc)
            if docstring:
                start_byte = self._find_next_content_byte(docstring.end_byte)

        # Adjust to line start for non-brace languages
        if not is_brace_based:
            func_line = func_def.start_point[0]
            body_line = body_node.start_point[0]
            if body_line > func_line:
                start_byte = self._find_line_start(start_byte)

        return (start_byte, end_byte)

    def _compute_inner_range(self, body_node: Node) -> Tuple[int, int]:
        """
        Get inner content range, excluding braces if present.

        Args:
            body_node: Body node (block, statement_block, etc.)

        Returns:
            Tuple of (start_byte, end_byte) for inner content
        """
        if not body_node.children:
            return (body_node.start_byte, body_node.end_byte)

        first_child = body_node.children[0]
        last_child = body_node.children[-1]

        first_text = self.doc.get_node_text(first_child) if first_child else ""
        last_text = self.doc.get_node_text(last_child) if last_child else ""

        if first_text == "{" and last_text == "}":
            return (first_child.end_byte, last_child.start_byte)

        return (body_node.start_byte, body_node.end_byte)

    def _find_leading_sibling_comments(
        self, func_def: Node, body_node: Node
    ) -> Optional[int]:
        """
        Find comments that appear between function signature and body block.

        In Python/Ruby, comments can appear as separate children between ':' and block.
        Example:
            def multiply(a, b):
                # This is a leading comment
                return a * b

        Args:
            func_def: Function definition node
            body_node: Body block node

        Returns:
            Start byte of first leading comment, or None if no leading comments
        """
        # Find body_node index among func_def children
        body_index = None
        for i, child in enumerate(func_def.children):
            if child == body_node:
                body_index = i
                break

        if body_index is None:
            return None

        # Walk backwards from body to find first comment
        first_comment_start = None
        for i in range(body_index - 1, -1, -1):
            child = func_def.children[i]

            # Check if this is a comment node
            if child.type in self.comment_types:
                first_comment_start = child.start_byte
            else:
                # Stop at first non-comment node (likely ':' or other syntax)
                break

        return first_comment_start

    def _find_next_content_byte(self, pos: int) -> int:
        """
        Find start of next line after position.

        Args:
            pos: Current byte position

        Returns:
            Byte position of next line start
        """
        text = self.doc.text
        newline_pos = text.find('\n', pos)
        if newline_pos == -1:
            return pos
        return newline_pos + 1

    def _find_line_start(self, pos: int) -> int:
        """
        Find start of line containing position.

        Preserves indentation for proper placeholder formatting.

        Args:
            pos: Byte position in text

        Returns:
            Start byte of line containing pos
        """
        text = self.doc.text
        line_start = text.rfind('\n', 0, pos)
        if line_start == -1:
            return 0
        return line_start + 1


__all__ = ["BodyRangeComputer"]

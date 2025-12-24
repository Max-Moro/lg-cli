"""
Python string literal processor with docstring filtering.

Handles Python string literals with special filtering to skip docstrings,
which should be processed by comment optimization instead.
"""

from __future__ import annotations

from ...optimizations.literals import StringLiteralProcessor
from ...tree_sitter_support import Node, TreeSitterDocument


class PythonStringLiteralProcessor(StringLiteralProcessor):
    """
    Specialized processor for Python string literals.

    Filters out docstrings (documentation strings) to avoid conflicts
    with comment optimization. Docstrings in Python are string literals
    that appear as the sole child of an expression_statement.

    Examples of docstrings (should be skipped):
    - Module docstring: triple-quoted string as first in file
    - Function docstring: triple-quoted string as first in function body
    - Class docstring: triple-quoted string as first in class body

    Examples of regular strings (should be processed):
    - Variable assignment: x = "string"
    - Return value: return "result"
    - Function argument: func("arg")
    """

    def process(self, node: Node, doc: TreeSitterDocument, source_text, profile, budget):
        """
        Process Python string literal node.

        Filters out docstrings and delegates regular strings to parent.

        Returns:
            TrimResult if optimization applied, None if docstring or no optimization
        """
        # Skip docstrings - they will be processed by comment optimization
        if self._is_docstring(node):
            return None

        # Delegate to parent StringLiteralProcessor for actual processing
        return super().process(node, doc, source_text, profile, budget)

    def _is_docstring(self, node: Node) -> bool:
        """
        Detect if string node is a docstring (documentation comment).

        In Python, docstrings are strings that serve as documentation:
        - Module docstring: first string literal in module
        - Function/method docstring: first string in function body
        - Class docstring: first string in class body

        AST pattern: string is sole child of expression_statement

        Args:
            node: String node to check

        Returns:
            True if node is a docstring, False otherwise
        """
        if not node.parent:
            return False

        parent = node.parent

        # Python-style docstrings: string inside expression_statement
        # expression_statement is used for standalone expressions (like docstrings)
        if parent.type == "expression_statement":
            # In Python, docstring is typically the only child of expression_statement
            # Verify it's actually a string literal, not some other expression
            if node.type == "string" and len(parent.children) == 1:
                return True

        return False

"""
Python trivial file detection.

Detects trivial __init__.py files that contain only:
- Docstrings
- Comments
- Re-exports (from .module import ...)
- __all__ declarations
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class PythonTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Python __init__.py files."""

    # Node types that indicate non-trivial content
    NON_TRIVIAL_TYPES = {
        "function_definition",
        "class_definition",
        "if_statement",
        "try_statement",
        "while_statement",
        "for_statement",
        "with_statement",
        "match_statement",
        "decorated_definition",
    }

    # Import types that are considered re-exports
    REEXPORT_TYPES = {
        "import_from_statement",
        "import_statement",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Python file is trivial."""
        # Only analyze __init__.py files
        if ctx.filename != "__init__.py":
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        # Parse and analyze AST
        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_init_file(doc)

    def _analyze_init_file(self, doc: TreeSitterDocument) -> bool:
        """Analyze __init__.py AST for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Skip comments
            if node_type == "comment":
                continue

            # Check expression statements (docstrings, __all__)
            if node_type == "expression_statement":
                if not self._is_docstring_or_all(child, doc):
                    return False
                continue

            # Non-trivial content found
            if node_type in self.NON_TRIVIAL_TYPES:
                return False

            # Allow only imports (re-exports)
            if node_type not in self.REEXPORT_TYPES:
                return False

        return True

    def _is_docstring_or_all(self, node, doc: TreeSitterDocument) -> bool:
        """Check if expression is docstring or __all__ assignment."""
        # Check children for string (docstring) or assignment to __all__
        for child in node.children:
            if child.type == "string":
                return True
            if child.type == "assignment":
                # Check if left side is __all__
                left = child.child_by_field_name("left")
                if left and doc.get_node_text(left) == "__all__":
                    return True
        return False


__all__ = ["PythonTrivialAnalyzer"]

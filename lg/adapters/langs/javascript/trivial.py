"""
JavaScript trivial file detection.

Detects trivial barrel files (index.js) that contain only:
- Comments
- Re-exports (export { ... } from './module')
"""

from __future__ import annotations

from ...optimizations.trivial_files.analyzer import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class JavaScriptTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial JavaScript barrel files."""

    BARREL_FILENAMES = {"index.js", "index.jsx", "index.mjs", "index.cjs"}

    NON_TRIVIAL_TYPES = {
        "function_declaration",
        "class_declaration",
        "variable_declaration",
        "expression_statement",
        "lexical_declaration",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if JavaScript file is trivial barrel."""
        if ctx.filename not in self.BARREL_FILENAMES:
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_barrel_file(doc)

    def _analyze_barrel_file(self, doc: TreeSitterDocument) -> bool:
        """Analyze barrel file for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Skip comments
            if node_type in ("comment", "multiline_comment"):
                continue

            # Non-trivial content
            if node_type in self.NON_TRIVIAL_TYPES:
                return False

            # For exports, check they are re-exports (have 'from')
            if node_type == "export_statement":
                if not self._is_reexport(child, doc):
                    return False
                continue

            # Side-effect imports are not trivial
            if node_type == "import_statement":
                return False

        return True

    def _is_reexport(self, node, _doc: TreeSitterDocument) -> bool:
        """Check if export statement is a re-export (has 'from' clause)."""
        for child in node.children:
            if child.type == "string":
                return True
        return False


__all__ = ["JavaScriptTrivialAnalyzer"]

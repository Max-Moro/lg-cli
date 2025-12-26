"""
Go trivial file detection.

Detects trivial doc.go files that contain only:
- Package clause
- Comments (package documentation)
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class GoTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Go doc.go files."""

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Go file is trivial doc.go."""
        if ctx.filename != "doc.go":
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_doc_file(doc)

    def _analyze_doc_file(self, doc: TreeSitterDocument) -> bool:
        """Analyze doc.go for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Allow package clause and comments
            if node_type in ("package_clause", "comment"):
                continue

            # Anything else = non-trivial
            return False

        return True


__all__ = ["GoTrivialAnalyzer"]

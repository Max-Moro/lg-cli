"""
Java trivial file detection.

Detects trivial package-info.java files that contain only:
- Package declaration
- Annotations
- Comments and Javadoc
- Import statements
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class JavaTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Java package-info.java files."""

    ALLOWED_TYPES = {
        "package_declaration",
        "import_declaration",
        "line_comment",
        "block_comment",
        "marker_annotation",
        "annotation",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Java file is trivial package-info."""
        if ctx.filename != "package-info.java":
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_package_info(doc)

    def _analyze_package_info(self, doc: TreeSitterDocument) -> bool:
        """Analyze package-info.java for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type not in self.ALLOWED_TYPES:
                return False

        return True


__all__ = ["JavaTrivialAnalyzer"]

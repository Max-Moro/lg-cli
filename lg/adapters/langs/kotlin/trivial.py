"""
Kotlin trivial file detection.

Detects trivial Kotlin files that contain only:
- Package header
- Import statements
- File annotations (@file:...)
- Comments
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class KotlinTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Kotlin package files."""

    TRIVIAL_FILENAMES = {"package.kt", "package-info.kt"}

    ALLOWED_TYPES = {
        "package_header",
        "import",
        "file_annotation",
        "block_comment",
        "line_comment",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Kotlin file is trivial package file."""
        if ctx.filename not in self.TRIVIAL_FILENAMES:
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_package_file(doc)

    def _analyze_package_file(self, doc: TreeSitterDocument) -> bool:
        """Analyze Kotlin file for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type not in self.ALLOWED_TYPES:
                return False

        return True


__all__ = ["KotlinTrivialAnalyzer"]

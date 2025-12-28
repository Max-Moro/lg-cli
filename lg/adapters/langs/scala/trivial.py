"""
Scala trivial file detection.

Detects trivial package.scala files that contain only:
- Package clause
- Import declarations
- Package object with only type aliases
- Comments
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class ScalaTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Scala package.scala files."""

    ALLOWED_TOP_LEVEL = {
        "package_clause",
        "import_declaration",
        "comment",
        "block_comment",
    }

    TRIVIAL_MEMBERS = {
        "type_definition",
        "import_declaration",
        "comment",
        "block_comment",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Scala file is trivial package.scala."""
        if ctx.filename != "package.scala":
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_package_object(doc)

    def _analyze_package_object(self, doc: TreeSitterDocument) -> bool:
        """Analyze package.scala for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type in self.ALLOWED_TOP_LEVEL:
                continue

            # Check package object body
            if child.type == "package_object":
                if self._has_non_trivial_members(child):
                    return False
                continue

            # Any other top-level = non-trivial
            return False

        return True

    def _has_non_trivial_members(self, package_obj) -> bool:
        """Check if package object has non-trivial members."""
        # Find template body
        for child in package_obj.children:
            if child.type == "template_body":
                for member in child.children:
                    # Skip braces and whitespace
                    if member.type in ("{", "}"):
                        continue
                    # Trivial members: type aliases, imports, comments
                    if member.type in self.TRIVIAL_MEMBERS:
                        continue
                    # Any other member = non-trivial
                    return True
        return False


__all__ = ["ScalaTrivialAnalyzer"]

"""
Rust trivial file detection.

Detects trivial mod.rs and lib.rs files that contain only:
- Module declarations (pub mod, mod)
- Use declarations (pub use, use)
- Attributes (#[...])
- Comments and doc comments
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class RustTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Rust mod.rs/lib.rs files."""

    TRIVIAL_FILENAMES = {"mod.rs", "lib.rs"}

    ALLOWED_TYPES = {
        "mod_item",           # mod declarations
        "use_declaration",    # use/re-exports
        "attribute_item",     # #[...] attributes
        "inner_attribute_item",  # #![...] inner attributes
        "line_comment",
        "block_comment",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if Rust file is trivial mod.rs/lib.rs."""
        if ctx.filename not in self.TRIVIAL_FILENAMES:
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_mod_file(doc)

    def _analyze_mod_file(self, doc: TreeSitterDocument) -> bool:
        """Analyze mod.rs/lib.rs for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type not in self.ALLOWED_TYPES:
                return False

        return True


__all__ = ["RustTrivialAnalyzer"]

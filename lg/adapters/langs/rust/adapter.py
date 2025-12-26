"""
Rust adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, ClassVar, Dict

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...comment_style import CommentStyle, RUST_STYLE_COMMENTS
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class RustCfg(CodeCfg):
    """Configuration for Rust adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> RustCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return RustCfg()

        cfg = RustCfg()
        cfg.general_load(d)

        # Rust-specific settings (currently none)

        return cfg


class RustDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_rust as tsrust
        return Language(tsrust.language())


class RustAdapter(CodeAdapter[RustCfg]):

    name = "rust"
    extensions = {".rs"}

    COMMENT_STYLE: ClassVar[CommentStyle] = RUST_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return RustDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create Rust-specific import classifier."""
        from .imports import RustImportClassifier
        return RustImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create Rust-specific import analyzer."""
        from .imports import RustImportAnalyzer
        return RustImportAnalyzer(classifier)

    def create_comment_analyzer(self, context):
        """Create Rust-specific comment analyzer."""
        from .comments import RustCommentAnalyzer
        return RustCommentAnalyzer(context.doc, self.COMMENT_STYLE)

    def get_code_descriptor(self):
        """Return Rust code descriptor."""
        from .code_profiles import RUST_CODE_DESCRIPTOR
        return RUST_CODE_DESCRIPTOR

    def create_literal_descriptor(self):
        """Create Rust literal descriptor."""
        from .literals import create_rust_descriptor
        return create_rust_descriptor()

    def should_skip(self, lightweight_ctx) -> bool:
        """
        Rust-specific file skip heuristics.
        Detects trivial mod.rs and lib.rs files.
        """
        from .trivial import RustTrivialAnalyzer
        analyzer = RustTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)


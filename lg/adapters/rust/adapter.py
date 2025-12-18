"""
Rust adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, ClassVar

from tree_sitter import Language

from ..code_analysis import CodeAnalyzer
from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..comment_style import CommentStyle, RUST_STYLE_COMMENTS
from ..tree_sitter_support import TreeSitterDocument


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

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


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

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create Rust-specific unified code analyzer."""
        from .code_analysis import RustCodeAnalyzer
        return RustCodeAnalyzer(doc)

    def create_comment_analyzer(self, doc: TreeSitterDocument, code_analyzer: CodeAnalyzer):
        """Create Rust-specific comment analyzer."""
        from .comment_analysis import RustCommentAnalyzer
        return RustCommentAnalyzer(doc, self.COMMENT_STYLE)

    def create_literal_descriptor(self):
        """Create Rust literal descriptor."""
        from .literals import create_rust_descriptor
        return create_rust_descriptor()

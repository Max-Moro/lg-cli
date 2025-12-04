"""
Rust adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer, LiteralOptimizer
from ..optimizations.literals import LiteralHandler
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

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Check if comment is Rust documentation."""
        stripped = comment_text.strip()
        # Rust uses /// and //! for documentation
        return stripped.startswith('///') or stripped.startswith('//!')

    def hook__get_literal_handler(
        self, root_optimizer: LiteralOptimizer  # noqa: F841
    ) -> LiteralHandler:
        """Provide Rust literal handler for vec!, lazy_static!, and raw strings."""
        from .literals import RustLiteralHandler
        return RustLiteralHandler()

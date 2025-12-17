"""
C adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_analysis import CodeAnalyzer
from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer, LanguageLiteralDescriptor
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class CCfg(CodeCfg):
    """Configuration for C adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> CCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return CCfg()

        cfg = CCfg()
        cfg.general_load(d)

        # C-specific settings (currently none)

        return cfg


class CDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_c as tsc
        return Language(tsc.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class CAdapter(CodeAdapter[CCfg]):

    name = "c"
    extensions = {".c", ".h"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return CDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create C-specific import classifier."""
        from .imports import CImportClassifier
        return CImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create C-specific import analyzer."""
        from .imports import CImportAnalyzer
        return CImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create C-specific unified code analyzer."""
        from .code_analysis import CCodeAnalyzer
        return CCodeAnalyzer(doc)

    def create_comment_analyzer(self, doc: TreeSitterDocument, code_analyzer: CodeAnalyzer):
        """Create C-specific comment analyzer."""
        from .comment_analysis import CStyleCommentAnalyzer
        return CStyleCommentAnalyzer(doc)

    def _get_comment_analyzer_class(self):
        """Get the C comment analyzer class."""
        from .comment_analysis import CStyleCommentAnalyzer
        return CStyleCommentAnalyzer

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create C literal descriptor."""
        from .literals import create_c_descriptor
        return create_c_descriptor()

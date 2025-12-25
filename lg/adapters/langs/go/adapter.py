"""
Go adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, ClassVar

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...comment_style import CommentStyle, GO_STYLE_COMMENTS
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer, LanguageLiteralDescriptor
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class GoCfg(CodeCfg):
    """Configuration for Go adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> GoCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return GoCfg()

        cfg = GoCfg()
        cfg.general_load(d)

        # Go-specific settings (currently none)

        return cfg


class GoDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_go as tsgo
        return Language(tsgo.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class GoAdapter(CodeAdapter[GoCfg]):

    name = "go"
    extensions = {".go"}

    COMMENT_STYLE: ClassVar[CommentStyle] = GO_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return GoDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create Go-specific import classifier."""
        from .imports import GoImportClassifier
        return GoImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create Go-specific import analyzer."""
        from .imports import GoImportAnalyzer
        return GoImportAnalyzer(classifier)

    def create_comment_analyzer(self, context):
        """Create Go-specific comment analyzer."""
        from .comment_analysis import GoCommentAnalyzer
        return GoCommentAnalyzer(context, self.COMMENT_STYLE)

    def get_code_descriptor(self):
        """Return Go code descriptor."""
        from .code_profiles import GO_CODE_DESCRIPTOR
        return GO_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Go literal descriptor."""
        from .literals import create_go_descriptor
        return create_go_descriptor()

"""
Scala adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, ClassVar

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...comment_style import CommentStyle, C_STYLE_COMMENTS
from ...context import LightweightContext
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ...optimizations.literals import LanguageLiteralDescriptor
from ...shared import LanguageCodeDescriptor
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class ScalaCfg(CodeCfg):
    """Configuration for Scala adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> ScalaCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return ScalaCfg()

        cfg = ScalaCfg()
        cfg.general_load(d)

        # Scala-specific settings (currently none)

        return cfg


class ScalaDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_scala as tsscala
        return Language(tsscala.language())


class ScalaAdapter(CodeAdapter[ScalaCfg]):

    name = "scala"
    extensions = {".scala", ".sc"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return ScalaDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create Scala-specific import classifier."""
        from .imports import ScalaImportClassifier
        return ScalaImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create Scala-specific import analyzer."""
        from .imports import ScalaImportAnalyzer
        return ScalaImportAnalyzer(classifier)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return Scala code descriptor."""
        from .code_profiles import SCALA_CODE_DESCRIPTOR
        return SCALA_CODE_DESCRIPTOR

    def create_comment_analyzer(self, context):
        """Create Scala-specific comment analyzer."""
        from .comments import ScalaCommentAnalyzer
        return ScalaCommentAnalyzer(context.doc, self.COMMENT_STYLE)

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Scala literal descriptor."""
        from .literals import create_scala_descriptor
        return create_scala_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Scala-specific file skip heuristics.
        Detects trivial package.scala files.
        """
        if not self.cfg.skip_trivial_files:
            return False

        from .trivial import ScalaTrivialAnalyzer
        analyzer = ScalaTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)

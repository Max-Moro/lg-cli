"""
Java adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, ClassVar, Dict

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...comment_style import CommentStyle, C_STYLE_COMMENTS
from ...context import LightweightContext
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer, LanguageLiteralDescriptor
from ...shared import LanguageCodeDescriptor
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class JavaCfg(CodeCfg):
    """Configuration for Java adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> JavaCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return JavaCfg()

        cfg = JavaCfg()
        cfg.general_load(d)

        # Java-specific settings (currently none)

        return cfg


class JavaDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_java as tsjava
        return Language(tsjava.language())


class JavaAdapter(CodeAdapter[JavaCfg]):

    name = "java"
    extensions = {".java"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return JavaDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create Java-specific import classifier."""
        from .imports import JavaImportClassifier
        return JavaImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create Java-specific import analyzer."""
        from .imports import JavaImportAnalyzer
        return JavaImportAnalyzer(classifier)

    def create_comment_analyzer(self, context):
        """Create Java-specific comment analyzer."""
        from .comments import JavaCommentAnalyzer
        return JavaCommentAnalyzer(context.doc, self.COMMENT_STYLE)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return Java code descriptor."""
        from .code_profiles import JAVA_CODE_DESCRIPTOR
        return JAVA_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Java literal descriptor."""
        from .literals import create_java_descriptor
        return create_java_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Java-specific file skip heuristics.
        Detects trivial package-info.java files.
        """
        from .trivial import JavaTrivialAnalyzer
        analyzer = JavaTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)

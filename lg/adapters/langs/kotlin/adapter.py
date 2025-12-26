"""
Kotlin adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, ClassVar, Dict

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
class KotlinCfg(CodeCfg):

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> KotlinCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return KotlinCfg()

        cfg = KotlinCfg()
        cfg.general_load(d)

        # Kotlin-specific settings (currently none)

        return cfg


class KotlinDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_kotlin as tskotlin
        return Language(tskotlin.language())


class KotlinAdapter(CodeAdapter[KotlinCfg]):

    name = "kotlin"
    extensions = {".kt", ".kts"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return KotlinDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create a Kotlin-specific import classifier."""
        from .imports import KotlinImportClassifier
        return KotlinImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create a Kotlin-specific import analyzer."""
        from .imports import KotlinImportAnalyzer
        return KotlinImportAnalyzer(classifier)

    def create_comment_analyzer(self, context):
        """Create Kotlin-specific comment analyzer."""
        from .comments import KotlinCommentAnalyzer
        return KotlinCommentAnalyzer(context.doc, self.COMMENT_STYLE)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return Kotlin code descriptor."""
        from .code_profiles import KOTLIN_CODE_DESCRIPTOR
        return KOTLIN_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Kotlin literal descriptor."""
        from .literals import create_kotlin_descriptor
        return create_kotlin_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Kotlin-specific file skip heuristics.
        Detects trivial package.kt files.
        """
        if not self.cfg.skip_trivial_files:
            return False

        from .trivial import KotlinTrivialAnalyzer
        analyzer = KotlinTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)

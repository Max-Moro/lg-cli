"""
JavaScript adapter core: configuration, document and adapter classes.
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
class JavaScriptCfg(CodeCfg):
    """Configuration for JavaScript adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> JavaScriptCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return JavaScriptCfg()

        cfg = JavaScriptCfg()
        cfg.general_load(d)

        # JavaScript-specific settings (currently none)

        return cfg


class JavaScriptDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_javascript as tsjs
        return Language(tsjs.language())


class JavaScriptAdapter(CodeAdapter[JavaScriptCfg]):

    name = "javascript"
    extensions = {".js", ".jsx", ".mjs", ".cjs"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return JavaScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create JavaScript-specific import classifier."""
        from .imports import JavaScriptImportClassifier
        return JavaScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create JavaScript-specific import analyzer."""
        from .imports import JavaScriptImportAnalyzer
        return JavaScriptImportAnalyzer(classifier)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return JavaScript code descriptor."""
        from .code_profiles import JAVASCRIPT_CODE_DESCRIPTOR
        return JAVASCRIPT_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create JavaScript literal descriptor."""
        from .literals import create_javascript_descriptor
        return create_javascript_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        JavaScript-specific file skip heuristics.
        Detects trivial barrel files (index.js).
        """
        from .trivial import JavaScriptTrivialAnalyzer
        analyzer = JavaScriptTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)

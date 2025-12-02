"""
JavaScript adapter core: configuration, document and adapter classes.
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

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class JavaScriptAdapter(CodeAdapter[JavaScriptCfg]):

    name = "javascript"
    extensions = {".js", ".jsx", ".mjs", ".cjs"}

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

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create JavaScript-specific unified code analyzer."""
        from .code_analysis import JavaScriptCodeAnalyzer
        return JavaScriptCodeAnalyzer(doc)

    def hook__get_literal_handler(
        self, root_optimizer: LiteralOptimizer
    ) -> LiteralHandler:
        """Provide JavaScript literal handler for template literals."""
        from .literals import JSLiteralHandler
        return JSLiteralHandler()

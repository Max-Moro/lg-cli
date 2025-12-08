"""
Scala adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..optimizations.literals import LanguageLiteralDescriptor
from ..tree_sitter_support import TreeSitterDocument


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

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class ScalaAdapter(CodeAdapter[ScalaCfg]):

    name = "scala"
    extensions = {".scala", ".sc"}

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

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create Scala-specific unified code analyzer."""
        from .code_analysis import ScalaCodeAnalyzer
        return ScalaCodeAnalyzer(doc)

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Scala literal descriptor for v2 optimizer."""
        from .literals import create_scala_descriptor
        return create_scala_descriptor()

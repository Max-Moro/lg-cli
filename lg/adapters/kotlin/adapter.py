"""
Kotlin adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..optimizations.literals_v2 import LanguageLiteralDescriptor
from ..tree_sitter_support import TreeSitterDocument


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

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class KotlinAdapter(CodeAdapter[KotlinCfg]):

    name = "kotlin"
    extensions = {".kt", ".kts"}

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

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create a Kotlin-specific unified code analyzer."""
        from .code_analysis import KotlinCodeAnalyzer
        return KotlinCodeAnalyzer(doc)

    # == Hooks used by Kotlin adapter ==

    def hook__remove_function_body(self, *args, **kwargs) -> None:
        """Kotlin-specific function body removal with KDoc preservation."""
        from .function_bodies import remove_function_body_with_kdoc
        remove_function_body_with_kdoc(*args, **kwargs)

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Kotlin literal descriptor for v2 optimizer."""
        from .literals_v2 import create_kotlin_descriptor
        return create_kotlin_descriptor()

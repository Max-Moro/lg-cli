"""
Kotlin adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext, ProcessingContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
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

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Kotlin-specific file skipping heuristics.
        """
        # Can add heuristics for generated files, etc.
        return False

    # == Hooks used by Kotlin adapter ==

    def get_comment_style(self) -> tuple[str, tuple[str, str], tuple[str, str]]:
        # Kotlin uses Java-style comments
        return "//", ("/*", "*/"), ("/**", "*/")

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Check if comment is KDoc documentation."""
        return comment_text.strip().startswith('/**')

    def is_docstring_node(self, node, doc: TreeSitterDocument) -> bool:
        """Kotlin has no docstring like Python, only KDoc comments."""
        return False

    def hook__remove_function_body(self, *args, **kwargs) -> None:
        """Kotlin-specific function body removal with KDoc preservation."""
        from .function_bodies import remove_function_body_with_kdoc
        remove_function_body_with_kdoc(*args, **kwargs)

    def hook__process_additional_literals(self, context: ProcessingContext, max_tokens: Optional[int]) -> None:
        """Process Kotlin-specific literals (collections listOf/mapOf/setOf)."""
        from .literals import process_kotlin_literals
        process_kotlin_literals(context, max_tokens)


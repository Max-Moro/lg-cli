"""
Python adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer, CommentOptimizer
from ..optimizations.literals import LanguageLiteralDescriptor
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class PythonCfg(CodeCfg):
    """Configuration for Python adapter."""
    skip_trivial_inits: bool = True  # Skip trivial __init__.py files

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> PythonCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return PythonCfg()

        cfg = PythonCfg()
        cfg.general_load(d)

        # Python-specific settings
        cfg.skip_trivial_inits = bool(d.get("skip_trivial_inits", True))

        return cfg


class PythonDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class PythonAdapter(CodeAdapter[PythonCfg]):

    name = "python"
    extensions = {".py"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return PythonDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create Python-specific import classifier."""
        from .imports import PythonImportClassifier
        return PythonImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create Python-specific import analyzer."""
        from .imports import PythonImportAnalyzer
        return PythonImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create Python-specific unified code analyzer."""
        from .code_analysis import PythonCodeAnalyzer
        return PythonCodeAnalyzer(doc)

    def create_comment_analyzer(self, doc: TreeSitterDocument):
        """Create Python-specific comment analyzer."""
        from .comment_analysis import PythonCommentAnalyzer
        return PythonCommentAnalyzer(doc)

    def _get_comment_analyzer_class(self):
        """Get the Python comment analyzer class."""
        from .comment_analysis import PythonCommentAnalyzer
        return PythonCommentAnalyzer

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Python literal descriptor."""
        from .literals import create_python_descriptor
        return create_python_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Python-specific file skip heuristics.
        """
        from .file_heuristics import should_skip_python_file
        return should_skip_python_file(lightweight_ctx, self.cfg.skip_trivial_inits)

    # == HOOKS used by Python adapter ==

    def hook__remove_function_body(self, *args, **kwargs) -> None:
        from .function_bodies import remove_function_body_with_definition
        remove_function_body_with_definition(*args, **kwargs)


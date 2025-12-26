"""
Python adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, ClassVar, Dict

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...comment_style import CommentStyle, HASH_STYLE_COMMENTS
from ...context import LightweightContext
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ...optimizations.literals import LanguageLiteralDescriptor
from ...shared import LanguageCodeDescriptor
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class PythonCfg(CodeCfg):
    """Configuration for Python adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> PythonCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return PythonCfg()

        cfg = PythonCfg()
        cfg.general_load(d)

        # Python-specific settings

        return cfg


class PythonDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())


class PythonAdapter(CodeAdapter[PythonCfg]):

    name = "python"
    extensions = {".py"}

    COMMENT_STYLE: ClassVar[CommentStyle] = HASH_STYLE_COMMENTS

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

    def create_comment_analyzer(self, context):
        """Create Python-specific comment analyzer."""
        from .comments import PythonCommentAnalyzer
        return PythonCommentAnalyzer(context.doc, self.COMMENT_STYLE)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return Python code descriptor."""
        from .code_profiles import PYTHON_CODE_DESCRIPTOR
        return PYTHON_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create Python literal descriptor."""
        from .literals import create_python_descriptor
        return create_python_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Python-specific file skip heuristics.
        Detects trivial __init__.py files.
        """
        if not self.cfg.skip_trivial_files:
            return False

        from .trivial import PythonTrivialAnalyzer
        analyzer = PythonTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)



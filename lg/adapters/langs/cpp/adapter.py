"""
C++ adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, ClassVar

from tree_sitter import Language

from ...code_base import CodeAdapter
from ...code_model import CodeCfg
from ...optimizations import ImportClassifier, TreeSitterImportAnalyzer, LanguageLiteralDescriptor
from ...shared import LanguageCodeDescriptor
from ...comment_style import CommentStyle, C_STYLE_COMMENTS
from ...tree_sitter_support import TreeSitterDocument


@dataclass
class CppCfg(CodeCfg):
    """Configuration for C++ adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> CppCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return CppCfg()

        cfg = CppCfg()
        cfg.general_load(d)

        # C++-specific settings (currently none)

        return cfg


class CppDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_cpp as tscpp
        return Language(tscpp.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class CppAdapter(CodeAdapter[CppCfg]):

    name = "cpp"
    extensions = {".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return CppDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create C++-specific import classifier."""
        from .imports import CppImportClassifier
        return CppImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create C++-specific import analyzer."""
        from .imports import CppImportAnalyzer
        return CppImportAnalyzer(classifier)

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return C++ code descriptor."""
        from .code_profiles import CPP_CODE_DESCRIPTOR
        return CPP_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create C++ literal descriptor."""
        from .literals import create_cpp_descriptor
        return create_cpp_descriptor()

"""
C adapter core: configuration, document and adapter classes.
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
class CCfg(CodeCfg):
    """Configuration for C adapter."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> CCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return CCfg()

        cfg = CCfg()
        cfg.general_load(d)

        # C-specific settings (currently none)

        return cfg


class CDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_c as tsc
        return Language(tsc.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class CAdapter(CodeAdapter[CCfg]):

    name = "c"
    extensions = {".c", ".h"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return CDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create C-specific import classifier."""
        from .imports import CImportClassifier
        return CImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create C-specific import analyzer."""
        from .imports import CImportAnalyzer
        return CImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create C-specific unified code analyzer."""
        from .code_analysis import CCodeAnalyzer
        return CCodeAnalyzer(doc)

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Check if comment is Doxygen documentation."""
        stripped = comment_text.strip()
        return stripped.startswith('/**') or stripped.startswith('///')

    def hook__get_literal_handler(
        self, root_optimizer: LiteralOptimizer
    ) -> LiteralHandler:
        """Provide C literal handler for struct arrays."""
        from .literals import CLiteralHandler
        return CLiteralHandler(root_optimizer)

    def create_literal_descriptor(self):
        """Create C literal descriptor for v2 optimizer."""
        from .literals_v2 import create_c_descriptor
        return create_c_descriptor()

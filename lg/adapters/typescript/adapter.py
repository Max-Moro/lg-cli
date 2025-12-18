"""
TypeScript adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, ClassVar

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..comment_style import CommentStyle, C_STYLE_COMMENTS
from ..optimizations.literals import LanguageLiteralDescriptor
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class TypeScriptCfg(CodeCfg):
    """Configuration for TypeScript adapter."""
    skip_barrel_files: bool = True  # Skip barrel files (index.ts with re-exports)
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> TypeScriptCfg:
        """Load configuration from YAML dictionary."""
        if not d:
            return TypeScriptCfg()

        cfg = TypeScriptCfg()
        cfg.general_load(d)

        # TypeScript-specific settings
        cfg.skip_barrel_files = bool(d.get("skip_barrel_files", True))

        return cfg


class TypeScriptDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_typescript as tsts
        if self.ext == "ts":
            # TS and TSX have two different grammars in one package
            return Language(tsts.language_typescript())
        elif self.ext == "tsx":
            return Language(tsts.language_tsx())
        else:
            # Default to TypeScript
            return Language(tsts.language_typescript())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class TypeScriptAdapter(CodeAdapter[TypeScriptCfg]):

    name = "typescript"
    extensions = {".ts", ".tsx"}

    COMMENT_STYLE: ClassVar[CommentStyle] = C_STYLE_COMMENTS

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return TypeScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create TypeScript-specific import classifier."""
        from .imports import TypeScriptImportClassifier
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create TypeScript-specific import analyzer."""
        from .imports import TypeScriptImportAnalyzer
        return TypeScriptImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Create TypeScript-specific unified code analyzer."""
        from .code_analysis import TypeScriptCodeAnalyzer
        return TypeScriptCodeAnalyzer(doc)

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create TypeScript literal descriptor."""
        from .literals import create_typescript_descriptor
        return create_typescript_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        TypeScript-specific file skip heuristics.
        """
        from .file_heuristics import should_skip_typescript_file
        return should_skip_typescript_file(lightweight_ctx, self.cfg.skip_barrel_files, self, self.tokenizer)

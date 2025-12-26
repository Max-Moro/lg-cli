"""
TypeScript adapter core: configuration, document and adapter classes.
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

    def get_code_descriptor(self) -> LanguageCodeDescriptor:
        """Return TypeScript code descriptor."""
        from .code_profiles import TYPESCRIPT_CODE_DESCRIPTOR
        return TYPESCRIPT_CODE_DESCRIPTOR

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create TypeScript literal descriptor."""
        from .literals import create_typescript_descriptor
        return create_typescript_descriptor()

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        TypeScript-specific file skip heuristics.
        Detects trivial barrel files (index.ts).
        """
        from .trivial import TypeScriptTrivialAnalyzer
        analyzer = TypeScriptTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)

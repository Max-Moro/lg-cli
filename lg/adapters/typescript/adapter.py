"""
TypeScript adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript адаптера."""
    skip_barrel_files: bool = True  # Пропускать barrel files (index.ts с реэкспортами)
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> TypeScriptCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return TypeScriptCfg()

        cfg = TypeScriptCfg()
        cfg.general_load(d)

        # TypeScript-специфичные настройки
        cfg.skip_barrel_files = bool(d.get("skip_barrel_files", True))

        return cfg


class TypeScriptDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_typescript as tsts
        if self.ext == "ts":
            # У TS и TSX — две разные грамматики в одном пакете.
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

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return TypeScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Создает TypeScript-специфичный классификатор импортов."""
        from .imports import TypeScriptImportClassifier
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает TypeScript-специфичный анализатор импортов."""
        from .imports import TypeScriptImportAnalyzer
        return TypeScriptImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Создает TypeScript-специфичный унифицированный анализатор кода."""
        from .code_analysis import TypeScriptCodeAnalyzer
        return TypeScriptCodeAnalyzer(doc)

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        TypeScript-специфичные эвристики пропуска файлов.
        """
        from .file_heuristics import should_skip_typescript_file
        return should_skip_typescript_file(lightweight_ctx, self.cfg.skip_barrel_files, self, self.tokenizer)

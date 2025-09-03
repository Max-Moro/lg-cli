"""
Tree-sitter based JavaScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

from .code_base import CodeAdapter
from .code_model import CodeCfg
from .import_utils import ImportClassifier, ImportAnalyzer, ImportInfo
from .range_edits import RangeEditor, PlaceholderGenerator
from .tree_sitter_support import TreeSitterDocument, Node


@dataclass
class JavaScriptCfg(CodeCfg):
    """Конфигурация для JavaScript адаптера."""


class JavaScriptTreeSitterDocument(TreeSitterDocument):

    def get_language_parser(self) -> Parser:
        TS = Language(tsts.language_typescript())
        TSX = Language(tsts.language_tsx())

        # TODO У TS и TSX — две разные грамматики в одном пакете.
        # Выбирать подходящую грамматику по расширению файла.

        return Parser(TSX)

class JavaScriptTreeSitterAdapter(TypeScriptTreeSitterAdapter):
    """Tree-sitter based JavaScript adapter (наследует от TypeScript)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}
    
    # JavaScript использует ту же логику, что и TypeScript,
    # но без типов (которые в любом случае обрабатываются Tree-sitter'ом)

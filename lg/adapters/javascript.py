"""
JavaScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from tree_sitter import Language, Parser

from .code_base import CodeAdapter
from .code_model import CodeCfg
from .tree_sitter_support import TreeSitterDocument


@dataclass
class JavaScriptCfg(CodeCfg):
    """Конфигурация для JavaScript адаптера."""

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> JavaScriptCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return JavaScriptCfg()

        cfg = JavaScriptCfg()
        cfg.general_load(d)

        # JavaScript-специфичные настройки

        return cfg


class JavaScriptDocument(TreeSitterDocument):

    def get_language_parser(self) -> Parser:
        import tree_sitter_javascript as tsjs
        # одна грамматика покрывает JS и JSX
        return Parser(Language(tsjs.language()))

class JavaScriptAdapter(CodeAdapter[JavaScriptCfg]):

    name = "javascript"
    extensions = {".js", ".jsx"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return JavaScriptDocument(text, ext)

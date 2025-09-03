"""
Tree-sitter based JavaScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Language, Parser

from .code_base import CodeAdapter
from .code_model import CodeCfg
from .tree_sitter_support import TreeSitterDocument


@dataclass
class JavaScriptCfg(CodeCfg):
    """Конфигурация для JavaScript адаптера."""
    # У JavaScript пока нет специфичных настроек


class JavaScriptTreeSitterDocument(TreeSitterDocument):

    def get_language_parser(self) -> Parser:
        import tree_sitter_javascript as tsjs
        # одна грамматика покрывает JS и JSX
        return Parser(Language(tsjs.language()))

class JavaScriptTreeSitterAdapter(CodeAdapter[JavaScriptCfg]):
    """Tree-sitter based JavaScript adapter (наследует от TypeScript)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return JavaScriptTreeSitterDocument(text, ext)

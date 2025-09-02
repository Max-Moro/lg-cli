"""
TypeScript/JavaScript адаптер.
Оптимизация листингов TypeScript и JavaScript кода.
"""

from __future__ import annotations

from .code_base import CodeAdapter, CodeDocument
from .code_model import TypeScriptCfg


class TypeScriptAdapter(CodeAdapter[TypeScriptCfg]):
    """Адаптер для TypeScript файлов (.ts, .tsx)."""
    
    name = "typescript"
    extensions = {".ts", ".tsx"}

    def parse_code(self, text: str) -> CodeDocument:
        """
        Парсит TypeScript код.
        TODO: Реализация парсинга TypeScript AST.
        """
        lines = text.splitlines()
        doc = CodeDocument(lines)
        
        # Заглушка - в реальной реализации здесь будет парсинг TypeScript
        # с помощью соответствующих библиотек (например, через tree-sitter или ts-morph)
        
        return doc


class JavaScriptAdapter(CodeAdapter[TypeScriptCfg]):
    """Адаптер для JavaScript файлов (.js, .jsx)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}

    def parse_code(self, text: str) -> CodeDocument:
        """
        Парсит JavaScript код.
        TODO: Реализация парсинга JavaScript AST.
        """
        lines = text.splitlines()
        doc = CodeDocument(lines)
        
        # Заглушка - использует ту же логику что и TypeScript
        # но без типов
        
        return doc

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """JavaScript использует C-style комментарии."""
        return "//", ("/*", "*/")

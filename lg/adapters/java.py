"""
Java адаптер.
Оптимизация листингов Java кода.
"""

from __future__ import annotations

from .code_base import CodeAdapter, CodeDocument
from .code_model import JavaCfg


class JavaAdapter(CodeAdapter[JavaCfg]):
    """Адаптер для Java файлов (.java)."""
    
    name = "java"
    extensions = {".java"}

    def parse_code(self, text: str) -> CodeDocument:
        """
        Парсит Java код.
        TODO: Реализация парсинга Java AST.
        """
        lines = text.splitlines()
        doc = CodeDocument(lines)
        
        # Заглушка - в реальной реализации здесь будет парсинг Java
        # с помощью соответствующих библиотек (например, через tree-sitter-java)
        
        return doc

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Java использует C-style комментарии."""
        return "//", ("/*", "*/")

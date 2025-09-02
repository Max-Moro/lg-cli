"""
Scala адаптер.
Оптимизация листингов Scala кода (2.x и 3.x).
"""

from __future__ import annotations

from .code_base import CodeAdapter, CodeDocument
from .code_model import ScalaCfg


class ScalaAdapter(CodeAdapter[ScalaCfg]):
    """Адаптер для Scala файлов (.scala)."""
    
    name = "scala"
    extensions = {".scala"}

    def parse_code(self, text: str) -> CodeDocument:
        """
        Парсит Scala код.
        TODO: Реализация парсинга Scala AST.
        """
        lines = text.splitlines()
        doc = CodeDocument(lines)
        
        # Заглушка - в реальной реализации здесь будет парсинг Scala
        # с помощью соответствующих библиотек (например, через tree-sitter-scala или scalameta)
        
        return doc

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Scala использует C-style комментарии."""
        return "//", ("/*", "*/")

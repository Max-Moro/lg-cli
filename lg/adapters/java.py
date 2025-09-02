"""
Java адаптер.
Оптимизация листингов Java кода.
"""

from __future__ import annotations

from dataclasses import dataclass

from .code_base import CodeAdapter, CodeDocument
from .code_model import CodeCfg


@dataclass
class JavaCfg(CodeCfg):
    """Конфигурация для Java адаптера."""
    
    def __post_init__(self):
        # Java-специфичные дефолты
        if not hasattr(self, '_java_defaults_applied'):
            self.public_api_only = True
            self.field_config.strip_trivial_accessors = True  # убираем геттеры/сеттеры
            self._java_defaults_applied = True


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

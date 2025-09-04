"""
Java adapter stub.
Will be implemented in M7 as lg/adapters/java/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


class JavaAdapter(CodeAdapter[CodeCfg]):
    """Java адаптер (заглушка для M7)."""

    name = "java"
    extensions = {".java"}

    def lang_flag__is_oop(self) -> bool:
        return True

    def lang_flag__with_access_modifiers(self) -> bool:
        return True

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Java использует C-style комментарии."""
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("Java adapter will be implemented in M7")

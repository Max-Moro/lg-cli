"""
JavaScript adapter stub.
Will be implemented in M7 as lg/adapters/javascript/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


class JavaScriptAdapter(CodeAdapter[CodeCfg]):
    """JavaScript адаптер (заглушка для M7)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}

    def lang_flag__is_oop(self) -> bool:
        return True

    def lang_flag__with_access_modifiers(self) -> bool:
        return False

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("JavaScript adapter will be implemented in M7")

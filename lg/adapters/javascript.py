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

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("JavaScript adapter will be implemented in M7")

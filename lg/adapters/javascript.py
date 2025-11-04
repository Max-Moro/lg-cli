"""
JavaScript adapter stub.
Will be implemented in M7 as lg/adapters/javascript/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


# noinspection PyAbstractClass
class JavaScriptAdapter(CodeAdapter[CodeCfg]):
    """JavaScript адаптер (заглушка для M7, будет реализован позже)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("JavaScript adapter will be implemented in M7")

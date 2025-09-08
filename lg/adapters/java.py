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

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("Java adapter will be implemented in M7")

"""
Scala adapter stub.
Will be implemented in M7 as lg/adapters/scala/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


# noinspection PyAbstractClass
class ScalaAdapter(CodeAdapter[CodeCfg]):
    """Scala адаптер (заглушка для M7, будет реализован позже)."""

    name = "scala"
    extensions = {".scala"}

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("Scala adapter will be implemented in M7")

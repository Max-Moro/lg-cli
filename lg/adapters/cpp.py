"""
C/C++ adapter stub.
Will be implemented in M7 as lg/adapters/cpp/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


# noinspection PyAbstractClass
class CppAdapter(CodeAdapter[CodeCfg]):
    """C/C++ adapter (stub for M7, will be implemented later)."""
    
    name = "cpp"
    extensions = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("C/C++ adapter will be implemented in M7")

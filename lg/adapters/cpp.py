"""
C/C++ adapter stub.
Will be implemented in M7 as lg/adapters/cpp/ package.
"""

from __future__ import annotations

from .code_base import CodeAdapter
from .code_model import CodeCfg


class CppAdapter(CodeAdapter[CodeCfg]):
    """C/C++ адаптер (заглушка для M7)."""
    
    name = "cpp"
    extensions = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}

    def lang_flag__is_oop(self) -> bool:
        return True  # C++ поддерживает ООП

    def lang_flag__with_access_modifiers(self) -> bool:
        return True  # C++ имеет public/private/protected

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """C/C++ использует C-style комментарии."""
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str):
        raise NotImplementedError("C/C++ adapter will be implemented in M7")

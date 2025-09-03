"""
C/C++ адаптер.
Оптимизация листингов C и C++ кода.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .code_base import CodeAdapter
from .code_model import CodeCfg


@dataclass
class CppCfg(CodeCfg):
    """Конфигурация для C/C++ адаптера."""
    header_mode: str = "declarations_only"
    macro_policy: str = "summarize_large"

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> CppCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return CppCfg()

        cfg = CppCfg()
        cfg.general_load(d)

        # C/C++-специфичные настройки
        cfg.header_mode = d.get("header_mode", "declarations_only")
        cfg.macro_policy = d.get("macro_policy", "summarize_large")

        return cfg


class CppAdapter(CodeAdapter[CppCfg]):
    """Адаптер для C/C++ файлов (.c, .cpp, .h, .hpp и др.)."""
    
    name = "cpp"
    extensions = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """C/C++ использует C-style комментарии."""
        return "//", ("/*", "*/")

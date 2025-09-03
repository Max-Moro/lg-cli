"""
Java адаптер.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .code_base import CodeAdapter
from .code_model import CodeCfg


@dataclass
class JavaCfg(CodeCfg):
    """Конфигурация для Java адаптера."""
    strip_trivial_accessors: bool = True
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> JavaCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return JavaCfg()

        cfg = JavaCfg()
        cfg.general_load(d)

        # Java-специфичные настройки

        return cfg


class JavaAdapter(CodeAdapter[JavaCfg]):

    name = "java"
    extensions = {".java"}

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Java использует C-style комментарии."""
        return "//", ("/*", "*/")

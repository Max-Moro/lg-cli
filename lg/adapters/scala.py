"""
Scala адаптер.
Оптимизация листингов Scala кода (2.x и 3.x).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .code_base import CodeAdapter
from .code_model import CodeCfg


@dataclass
class ScalaCfg(CodeCfg):
    """Конфигурация для Scala адаптера."""
    keep_given_using: bool = True
    case_class_policy: str = "signature_only"
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> ScalaCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return ScalaCfg()

        cfg = ScalaCfg()
        cfg.general_load(d)

        # Scala-специфичные настройки
        cfg.keep_given_using = bool(d.get("keep_given_using", True))
        cfg.case_class_policy = d.get("case_class_policy", "signature_only")

        return cfg


class ScalaAdapter(CodeAdapter[ScalaCfg]):

    name = "scala"
    extensions = {".scala"}

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Scala использует C-style комментарии."""
        return "//", ("/*", "*/")

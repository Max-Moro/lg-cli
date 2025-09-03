"""
Scala адаптер.
Оптимизация листингов Scala кода (2.x и 3.x).
"""

from __future__ import annotations

from dataclasses import dataclass

from .code_base import CodeAdapter
from .code_model import CodeCfg


@dataclass
class ScalaCfg(CodeCfg):
    """Конфигурация для Scala адаптера."""
    
    def __post_init__(self):
        # Scala-специфичные настройки
        if not hasattr(self, '_scala_defaults_applied'):
            self.lang_specific.setdefault("keep_given_using", True)
            self.lang_specific.setdefault("case_class_policy", "signature_only")
            self._scala_defaults_applied = True


class ScalaAdapter(CodeAdapter[ScalaCfg]):
    """Адаптер для Scala файлов (.scala)."""
    
    name = "scala"
    extensions = {".scala"}

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Scala использует C-style комментарии."""
        return "//", ("/*", "*/")

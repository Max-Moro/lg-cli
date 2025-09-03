"""
C/C++ адаптер.
Оптимизация листингов C и C++ кода.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .code_base import CodeAdapter
from .code_model import CodeCfg


@dataclass
class CppCfg(CodeCfg):
    """Конфигурация для C/C++ адаптера."""
    
    def __post_init__(self):
        # C/C++-специфичные настройки
        if not hasattr(self, '_cpp_defaults_applied'):
            # В заголовках (.h/.hpp) обычно нужны только объявления
            self.lang_specific.setdefault("header_mode", "declarations_only")
            self.lang_specific.setdefault("macro_policy", "summarize_large")
            self._cpp_defaults_applied = True


class CppAdapter(CodeAdapter[CppCfg]):
    """Адаптер для C/C++ файлов (.c, .cpp, .h, .hpp и др.)."""
    
    name = "cpp"
    extensions = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}

    def should_skip(self, path: Path, text: str, ext: str) -> bool:
        """
        C/C++ специфичные эвристики пропуска.
        Например, очень большие автогенерированные заголовки.
        """
        # Проверяем на автогенерированные файлы
        if "auto-generated" in text.lower() or "generated automatically" in text.lower():
            return True
        
        return super().should_skip(path, text)

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """C/C++ использует C-style комментарии."""
        return "//", ("/*", "*/")

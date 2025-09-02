"""
Расширенный Python адаптер с поддержкой новой архитектуры кода.
Заменяет существующий lg.adapters.python после завершения разработки.
"""

from __future__ import annotations

from pathlib import Path

from .code_base import CodeAdapter, CodeDocument
from .code_model import PythonCfg


class PythonAdapter(CodeAdapter[PythonCfg]):
    """Адаптер для Python файлов (.py)."""
    
    name = "python"
    extensions = {".py"}

    def should_skip(self, path: Path, text: str) -> bool:
        """
        Python-специфичные эвристики пропуска.
        Включает логику для __init__.py из существующего адаптера.
        """
        # Сохраняем существующую логику для __init__.py
        if path.name == "__init__.py":
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
            # Используем конфигурацию из существующего адаптера
            limit = 1  # trivial_init_max_noncomment из старого кода
            if len(significant) <= limit and all(
                ln in ("pass", "...") for ln in significant
            ):
                return True

        return super().should_skip(path, text)

    def parse_code(self, text: str) -> CodeDocument:
        """
        Парсит Python код.
        TODO: Реализация парсинга Python AST через ast модуль.
        """
        lines = text.splitlines()
        doc = CodeDocument(lines)
        
        # Заглушка - в реальной реализации здесь будет парсинг Python AST
        # с помощью встроенного модуля ast или tree-sitter-python
        
        return doc

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        """Python использует # для комментариев и triple quotes для docstrings."""
        return "#", ('"""', '"""')

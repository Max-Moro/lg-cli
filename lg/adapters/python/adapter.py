"""
Python adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import ProcessingContext
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class PythonCfg(CodeCfg):
    """Конфигурация для Python адаптера."""
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> PythonCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return PythonCfg()

        cfg = PythonCfg()
        cfg.general_load(d)

        # Python-специфичные настройки
        cfg.skip_trivial_inits = bool(d.get("skip_trivial_inits", True))
        cfg.trivial_init_max_noncomment = int(d.get("trivial_init_max_noncomment", 1))

        return cfg


class PythonDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class PythonAdapter(CodeAdapter[PythonCfg]):

    name = "python"
    extensions = {".py"}

    def lang_flag__is_oop(self) -> bool:
        return True

    def lang_flag__with_access_modifiers(self) -> bool:
        return False

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "#", ('"""', '"""')

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return PythonDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает Python-специфичный классификатор импортов."""
        from .imports import PythonImportClassifier
        return PythonImportClassifier(external_patterns)
    
    def create_import_analyzer(self, classifier):
        """Создает Python-специфичный анализатор импортов."""
        from .imports import PythonImportAnalyzer
        return PythonImportAnalyzer(classifier)
    
    def should_skip(self, path: Path, text: str, ext: str) -> bool:
        """
        Python-специфичные эвристики пропуска.
        """
        if path.name == "__init__.py":
            # Проверяем на тривиальные __init__.py файлы
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]

            skip_trivial = self.cfg.skip_trivial_inits
            limit = self.cfg.trivial_init_max_noncomment

            if not skip_trivial:
                return False

            # Пустой файл должен быть пропущен
            if len(significant) == 0:
                return True

            # Файлы с только pass/... в пределах лимита должны быть пропущены
            if len(significant) <= limit and all(
                    ln in ("pass", "...") for ln in significant
            ):
                return True

        return False

"""
Python adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer, CommentOptimizer
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class PythonCfg(CodeCfg):
    """Конфигурация для Python адаптера."""
    skip_trivial_inits: bool = True  # Пропускать тривиальные __init__.py

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> PythonCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return PythonCfg()

        cfg = PythonCfg()
        cfg.general_load(d)

        # Python-специфичные настройки
        cfg.skip_trivial_inits = bool(d.get("skip_trivial_inits", True))

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

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return PythonDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Создает Python-специфичный классификатор импортов."""
        from .imports import PythonImportClassifier
        return PythonImportClassifier(external_patterns)
    
    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает Python-специфичный анализатор импортов."""
        from .imports import PythonImportAnalyzer
        return PythonImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Создает Python-специфичный унифицированный анализатор кода."""
        from .code_analysis import PythonCodeAnalyzer
        return PythonCodeAnalyzer(doc)

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Python-специфичные эвристики пропуска.
        """
        from .file_heuristics import should_skip_python_file
        return should_skip_python_file(lightweight_ctx, self.cfg.skip_trivial_inits)

    # == ХУКИ, которые использует Python адаптер ==

    def hook__remove_function_body(self, *args, **kwargs) -> None:
        from .function_bodies import remove_function_body_with_definition
        remove_function_body_with_definition(*args, **kwargs)

    def get_comment_style(self) -> tuple[str, tuple[str, str], tuple[str, str]]:
        return "#", ('"""', '"""'), ('"""', '"""')

    def is_documentation_comment(self, comment_text: str) -> bool:
        return False # Используется явный захват в `QUERIES["comments"]` — capture_name == "docstring"

    def hook__extract_first_sentence(self, root_optimizer: CommentOptimizer, text: str) -> str:
        from .comments import extract_first_sentence
        return extract_first_sentence(text)

    def hook__smart_truncate_comment(self, root_optimizer: CommentOptimizer, comment_text: str, max_tokens: int, tokenizer) -> str:
        from .comments import smart_truncate_comment
        return smart_truncate_comment(comment_text, max_tokens, tokenizer)


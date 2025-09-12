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
        # Пропускаем тривиальные __init__.py если включена соответствующая опция
        if self.cfg.skip_trivial_inits:
            if self._is_trivial_init_file(lightweight_ctx):
                return True

        return False

    @staticmethod
    def _is_trivial_init_file(lightweight_ctx: LightweightContext) -> bool:
        """
        Пропуск тривиальных __init__.py при включённом cfg.skip_trivial_inits:
        - пустой файл
        - только 'pass' / '...'
        - только переэкспорт публичного API (относительные from-импорты, __all__)
        Комментарии сами по себе НЕ делают файл тривиальным (комментарии могут быть полезны).
        """
        # Только для __init__.py
        if lightweight_ctx.filename != "__init__.py":
            return False

        text = lightweight_ctx.raw_text or ""
        stripped = text.strip()

        # Пустой файл — тривиальный
        if stripped == "":
            return True

        lines = text.splitlines()

        # Выделяем строки без пустых и без комментариев для классификации
        non_comment_lines = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith("#"):
                # Комментарии не учитываем в классификации (они не делают файл тривиальным)
                continue
            non_comment_lines.append(ln)

        # Если в файле есть только комментарии — НЕ тривиальный
        if not non_comment_lines:
            return False

        def is_pass_or_ellipsis(s: str) -> bool:
            return s in ("pass", "...")

        def is_relative_from_import(s: str) -> bool:
            # from .pkg import X, Y
            if not s.startswith("from "):
                return False
            rest = s[5:].lstrip()
            return rest.startswith(".")

        def is_all_assign_start(s: str) -> bool:
            # __all__ = [...]
            return s.startswith("__all__")

        in_import_paren = False
        in_all_list = False

        for ln in non_comment_lines:
            if in_import_paren:
                # Продолжаем, пока не закроется группа импорта
                if ")" in ln:
                    in_import_paren = False
                continue

            if in_all_list:
                # Разрешаем многострочный список в __all__
                if "]" in ln:
                    in_all_list = False
                continue

            if is_pass_or_ellipsis(ln):
                continue

            if is_relative_from_import(ln):
                # Разрешаем многострочные импорты с '('
                if ln.endswith("(") or ln.endswith("\\") or "(" in ln and ")" not in ln:
                    in_import_paren = True
                continue

            if is_all_assign_start(ln):
                # Разрешаем многострочный __all__ = [
                if "[" in ln and "]" not in ln:
                    in_all_list = True
                continue

            # Любая другая конструкция делает файл нетривиальным
            return False

        # Если добрались сюда — все нетиповые строки допустимы → файл тривиальный
        return True


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


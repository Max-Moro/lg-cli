"""
Kotlin adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext, ProcessingContext
from ..optimizations import ImportClassifier, TreeSitterImportAnalyzer
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class KotlinCfg(CodeCfg):

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> KotlinCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return KotlinCfg()

        cfg = KotlinCfg()
        cfg.general_load(d)

        # Kotlin-специфичные настройки (на данный момент нет)

        return cfg


class KotlinDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_kotlin as tskotlin
        return Language(tskotlin.language())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class KotlinAdapter(CodeAdapter[KotlinCfg]):

    name = "kotlin"
    extensions = {".kt", ".kts"}

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return KotlinDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Создает Kotlin-специфичный классификатор импортов."""
        from .imports import KotlinImportClassifier
        return KotlinImportClassifier(external_patterns)
    
    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает Kotlin-специфичный анализатор импортов."""
        from .imports import KotlinImportAnalyzer
        return KotlinImportAnalyzer(classifier)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Создает Kotlin-специфичный унифицированный анализатор кода."""
        from .code_analysis import KotlinCodeAnalyzer
        return KotlinCodeAnalyzer(doc)

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Kotlin-специфичные эвристики пропуска файлов.
        """
        # Можно добавить эвристики, например, для сгенерированных файлов
        return False

    # == ХУКИ, которые использует Kotlin адаптер ==

    def get_comment_style(self) -> tuple[str, tuple[str, str], tuple[str, str]]:
        # Kotlin использует Java-style комментарии
        return "//", ("/*", "*/"), ("/**", "*/")

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Проверяет, является ли комментарий KDoc документацией."""
        return comment_text.strip().startswith('/**')

    def is_docstring_node(self, node, doc: TreeSitterDocument) -> bool:
        """В Kotlin нет docstring как в Python, только KDoc комментарии."""
        return False

    def hook__remove_function_body(self, *args, **kwargs) -> None:
        """Kotlin-специфичная обработка удаления тел функций с сохранением KDoc."""
        from .function_bodies import remove_function_body_with_kdoc
        remove_function_body_with_kdoc(*args, **kwargs)

    def hook__process_additional_literals(self, context: ProcessingContext, max_tokens: Optional[int]) -> None:
        """Обрабатывает Kotlin-специфичные литералы (коллекции listOf/mapOf/setOf)."""
        from .literals import process_kotlin_literals
        process_kotlin_literals(context, max_tokens)


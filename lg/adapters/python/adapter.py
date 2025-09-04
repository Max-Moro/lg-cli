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
from ..context import ProcessingContext, LightweightContext
from ..tree_sitter_support import TreeSitterDocument, Node


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
    
    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Python-специфичные эвристики пропуска.
        """
        if lightweight_ctx.filename == "__init__.py":
            # Проверяем на тривиальные __init__.py файлы
            significant = [
                ln.strip()
                for ln in lightweight_ctx.raw_text.splitlines()
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

    def is_public_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет публичность элемента Python по соглашениям об underscore.
        
        Правила:
        - Имена, начинающиеся с одного _ считаются "protected" (внутренние)
        - Имена, начинающиеся с двух __ считаются "private" 
        - Имена без _ или с trailing _ считаются публичными
        - Специальные методы __method__ считаются публичными
        """
        # Получаем имя элемента
        element_name = self._get_element_name(node, context)
        if not element_name:
            return True  # Если имя не найдено, считаем публичным
        
        # Специальные методы Python (dunder methods) считаются публичными
        if element_name.startswith("__") and element_name.endswith("__"):
            return True
        
        # Имена с двумя подчеркиваниями в начале - приватные
        if element_name.startswith("__"):
            return False
        
        # Имена с одним подчеркиванием в начале - защищенные (считаем приватными)
        if element_name.startswith("_"):
            return False
        
        # Все остальные - публичные
        return True

    def is_exported_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет, экспортируется ли элемент Python.
        
        В Python экспорт определяется через __all__ или по умолчанию все публичные элементы.
        Пока упрощенная реализация - считаем все публичные элементы экспортируемыми.
        """
        # TODO: Реализовать проверку __all__ в будущих итерациях
        return self.is_public_element(node, context)

    def _get_element_name(self, node: Node, context: ProcessingContext) -> Optional[str]:
        """
        Извлекает имя элемента из узла Tree-sitter.
        """
        # Ищем дочерний узел с именем функции/класса/метода
        for child in node.children:
            if child.type == "identifier":
                return context.get_node_text(child)
        
        # Для некоторых типов узлов имя может быть в поле name
        name_node = node.child_by_field_name("name")
        if name_node:
            return context.get_node_text(name_node)
        
        return None

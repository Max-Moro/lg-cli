"""
Python adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext, ProcessingContext
from ..optimizations import FieldsClassifier, ImportClassifier, TreeSitterImportAnalyzer, CommentOptimizer
from ..structure_analysis import CodeStructureAnalyzer
from ..tree_sitter_support import TreeSitterDocument, Node


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

    def create_import_classifier(self, external_patterns: List[str] = None) -> ImportClassifier:
        """Создает Python-специфичный классификатор импортов."""
        from .imports import PythonImportClassifier
        return PythonImportClassifier(external_patterns)
    
    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает Python-специфичный анализатор импортов."""
        from .imports import PythonImportAnalyzer
        return PythonImportAnalyzer(classifier)

    def create_fields_classifier(self, doc: TreeSitterDocument) -> FieldsClassifier:
        """Создает языко-специфичный классификатор конструкторов и полей."""
        from .fields import PythonFieldsClassifier
        return PythonFieldsClassifier(doc)

    def create_structure_analyzer(self, doc: TreeSitterDocument) -> CodeStructureAnalyzer:
        """Создает Python-специфичный анализатор структуры кода."""
        from .structure_analysis import PythonCodeStructureAnalyzer
        return PythonCodeStructureAnalyzer(doc)

    def collect_language_specific_private_elements(self, context: ProcessingContext) -> List[Tuple[Node, str]]:
        """
        Собирает Python-специфичные приватные элементы для public API фильтрации.
        
        В Python обычно достаточно универсальной логики для functions/methods/classes,
        но можно добавить специфичные проверки для модулей, __all__, и т.д.
        """
        # В Python пока используем только универсальную логику
        # В будущем можно добавить специфичные элементы:
        # - Проверки __all__ для определения экспортируемых элементов
        # - Обработку модульных переменных
        # - Специфичную логику для property/classmethod/staticmethod
        return []

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

    def is_public_element(self, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Определяет публичность элемента Python по соглашениям об underscore.
        
        Правила:
        - Имена, начинающиеся с одного _ считаются "protected" (внутренние)
        - Имена, начинающиеся с двух __ считаются "private" 
        - Имена без _ или с trailing _ считаются публичными
        - Специальные методы __method__ считаются публичными
        """
        # Получаем имя элемента
        element_name = self._get_element_name(node, doc)
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

    def is_exported_element(self, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Определяет, экспортируется ли элемент Python.
        
        В Python экспорт определяется через __all__ или по умолчанию все публичные элементы.
        Пока упрощенная реализация - считаем все публичные элементы экспортируемыми.
        """
        # TODO: Реализовать проверку __all__ в будущих итерациях
        return self.is_public_element(node, doc)

    @staticmethod
    def _get_element_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
        """
        Извлекает имя элемента из узла Tree-sitter.
        """
        # Специальная обработка для assignments
        if node.type == "assignment":
            # В assignment левая часть - это имя переменной
            for child in node.children:
                if child.type == "identifier":
                    return doc.get_node_text(child)
        
        # Ищем дочерний узел с именем функции/класса/метода
        for child in node.children:
            if child.type == "identifier":
                return doc.get_node_text(child)
        
        # Для некоторых типов узлов имя может быть в поле name
        name_node = node.child_by_field_name("name")
        if name_node:
            return doc.get_node_text(name_node)
        
        return None

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

    def hook__smart_truncate_comment(self, root_optimizer: CommentOptimizer, comment_text: str, max_length: int) -> str:
        from .comments import smart_truncate_comment
        return smart_truncate_comment(comment_text, max_length)

    def collect_language_specific_private_elements(self, context: ProcessingContext) -> List[Tuple[Node, str]]:
        """
        Собирает Python-специфичные приватные элементы для public API фильтрации.
        
        Включает обработку переменных/assignments и других Python-специфичных конструкций.
        """
        from .public_api import PythonPublicApiCollector
        collector = PythonPublicApiCollector(self)
        return collector.collect_private_elements(context)

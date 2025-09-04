"""
TypeScript adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import ProcessingContext
from ..range_edits import RangeEditor, PlaceholderGenerator
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript адаптера."""
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> TypeScriptCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return TypeScriptCfg()

        cfg = TypeScriptCfg()
        cfg.general_load(d)

        # TypeScript-специфичные настройки

        return cfg


class TypeScriptDocument(TreeSitterDocument):

    def get_language(self) -> Language:
        import tree_sitter_typescript as tsts
        if self.ext == "ts":
            # У TS и TSX — две разные грамматики в одном пакете.
            return Language(tsts.language_typescript())
        elif self.ext == "tsx":
            return Language(tsts.language_tsx())
        else:
            # Default to TypeScript
            return Language(tsts.language_typescript())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


class TypeScriptAdapter(CodeAdapter[TypeScriptCfg]):

    name = "typescript"
    extensions = {".ts", ".tsx"}

    def lang_flag__is_oop(self) -> bool:
        return True

    def lang_flag__with_access_modifiers(self) -> bool:
        return True

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return TypeScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает TypeScript-специфичный классификатор импортов."""
        from .imports import TypeScriptImportClassifier
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier):
        """Создает TypeScript-специфичный анализатор импортов."""
        from .imports import TypeScriptImportAnalyzer
        return TypeScriptImportAnalyzer(classifier)

    def hook__strip_function_bodies_v2(self, context: ProcessingContext) -> None:
        """Новая версия хука для обработки стрелочных функций через ProcessingContext."""
        self._strip_arrow_functions_v2(context)

    def hook__strip_function_bodies(
        self,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        meta: Dict[str, Any]
    ) -> None:
        """DEPRECATED: используйте hook__strip_function_bodies_v2."""
        self._strip_arrow_functions(doc, editor, meta)
    
    def _strip_arrow_functions_v2(self, context: ProcessingContext) -> None:
        """Новая версия обработки стрелочных функций через ProcessingContext."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Ищем стрелочные функции отдельно через re-query
        arrow_functions = [n for n, c in context.query("functions") if n.type == "arrow_function"]
        
        for node in arrow_functions:
            # Найти тело стрелочной функции
            body_node = None
            for child in node.children:
                if child.type in ("statement_block", "expression"):
                    body_node = child
                    break
            
            if not body_node:
                continue
                
            arrow_text = context.get_node_text(body_node)
            start_line, end_line = context.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Только стрипим многострочные стрелочные функции
            should_strip = lines_count > 1 and context.should_strip_function_body(arrow_text, lines_count, cfg)
            
            if should_strip:
                # Используем удобный метод контекста
                context.remove_function_body(
                    body_node,
                    func_type="function",
                    placeholder_style=self.cfg.placeholders.style
                )

    def _strip_arrow_functions(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """Обрабатывает стрелочные функции в TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем стрелочные функции отдельно через re-query
        arrow_functions = [n for n, c in doc.query("functions") if n.type == "arrow_function"]
        
        for node in arrow_functions:
            # Найти тело стрелочной функции
            body_node = None
            for child in node.children:
                if child.type in ("statement_block", "expression"):
                    body_node = child
                    break
            
            if not body_node:
                continue
                
            start_byte, end_byte = doc.get_node_range(body_node)
            
            arrow_text = doc.get_node_text(body_node)
            start_line, end_line = doc.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Только стрипим многострочные стрелочные функции
            if lines_count > 1 and super()._should_strip_function_body(cfg, arrow_text, lines_count):
                placeholder = placeholder_gen.create_function_placeholder(
                    lines_removed=lines_count,
                    bytes_removed=end_byte - start_byte,
                    style=self.cfg.placeholders.style
                )
                
                editor.add_replacement(
                    start_byte, end_byte, placeholder,
                    type="arrow_function_body_removal",
                    is_placeholder=True,
                    lines_removed=lines_count
                )
                
                meta["code.removed.functions"] += 1

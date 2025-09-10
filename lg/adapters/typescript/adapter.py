"""
TypeScript adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import LightweightContext
from ..optimizations import FieldsClassifier, ImportClassifier, TreeSitterImportAnalyzer
from ..tree_sitter_support import TreeSitterDocument


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript адаптера."""
    skip_barrel_files: bool = True  # Пропускать barrel files (index.ts с реэкспортами)
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> TypeScriptCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return TypeScriptCfg()

        cfg = TypeScriptCfg()
        cfg.general_load(d)

        # TypeScript-специфичные настройки
        cfg.skip_barrel_files = bool(d.get("skip_barrel_files", True))

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

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return TypeScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str] = None) -> ImportClassifier:
        """Создает TypeScript-специфичный классификатор импортов."""
        from .imports import TypeScriptImportClassifier
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Создает TypeScript-специфичный анализатор импортов."""
        from .imports import TypeScriptImportAnalyzer
        return TypeScriptImportAnalyzer(classifier)

    def create_fields_classifier(self, doc: TreeSitterDocument) -> FieldsClassifier:
        """Создает языко-специфичный классификатор конструкторов и полей."""
        from .fields import TypeScriptFieldsClassifier
        return TypeScriptFieldsClassifier(doc)

    def create_code_analyzer(self, doc: TreeSitterDocument):
        """Создает TypeScript-специфичный унифицированный анализатор кода."""
        from .code_analysis import TypeScriptCodeAnalyzer
        return TypeScriptCodeAnalyzer(doc)


    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        TypeScript-специфичные эвристики пропуска файлов.
        """
        # Пропускаем barrel files если включена соответствующая опция
        if self.cfg.skip_barrel_files:
            if self._is_barrel_file(lightweight_ctx):
                return True
        
        # Можно добавить другие эвристики пропуска для TypeScript
        return False


    def _is_barrel_file(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Определяет, является ли файл barrel file (index.ts или содержит только реэкспорты).
        Использует ленивую инициализацию - сначала простые эвристики, затем парсинг если нужно.
        """
        # Быстрая проверка по имени файла
        if lightweight_ctx.filename in ("index.ts", "index.tsx"):
            return True
        
        # Анализируем содержимое текстуально - если большинство строк содержат export ... from
        lines = lightweight_ctx.raw_text.split('\n')
        export_lines = 0
        non_empty_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                non_empty_lines += 1
                if 'export' in stripped and 'from' in stripped:
                    export_lines += 1
        
        # Если нет значимых строк, не barrel file
        if non_empty_lines == 0:
            return False
        
        # Эвристика: если больше 70% строк - реэкспорты, считаем barrel file
        export_ratio = export_lines / non_empty_lines
        
        # Если очевидно barrel file (много реэкспортов), возвращаем True
        if export_ratio > 0.7:
            return True
        
        # Если очевидно НЕ barrel file (мало реэкспортов), возвращаем False
        if export_ratio < 0.3:
            return False
        
        # Для промежуточных случаев (30-70%) используем ленивую инициализацию Tree-sitter
        # для более точного анализа структуры файла
        try:
            full_context = lightweight_ctx.get_full_context(self)
            return self._deep_barrel_file_analysis(full_context.doc)
        except Exception:
            # Если Tree-sitter парсинг не удался, полагаемся на текстовую эвристику
            return export_ratio > 0.5

    @staticmethod
    def _deep_barrel_file_analysis(doc: TreeSitterDocument) -> bool:
        """
        Глубокий анализ barrel file через Tree-sitter парсинг.
        Вызывается только в сложных случаях.
        """
        try:
            # Ищем все export statements
            exports = doc.query("exports")
            export_count = len(exports)
            
            # Ищем re-export statements (export ... from ...)
            reexport_count = 0
            for node, capture_name in exports:
                node_text = doc.get_node_text(node)
                if ' from ' in node_text:
                    reexport_count += 1
            
            # Также ищем обычные объявления (functions, classes, interfaces)
            functions = doc.query("functions")
            classes = doc.query("classes")
            interfaces = doc.query("interfaces")
            
            declaration_count = len(functions) + len(classes) + len(interfaces)
            
            # Barrel file если:
            # 1. Много реэкспортов и мало собственных объявлений
            # 2. Или очень высокий процент реэкспортов
            if export_count > 0:
                reexport_ratio = reexport_count / export_count
                return reexport_ratio > 0.6 and declaration_count < 3
            
            return False
            
        except Exception:
            # При ошибках парсинга возвращаем False
            return False

"""
Kotlin import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class KotlinImportClassifier(ImportClassifier):
    """Kotlin-specific import classifier."""
    
    def __init__(self, external_patterns: List[str] = []):
        self.external_patterns = external_patterns
        
        # Стандартные библиотеки JVM и Kotlin
        self.standard_packages = {
            'java', 'javax', 'kotlin', 'kotlinx',
            'android', 'androidx',
            'org.junit', 'org.hamcrest', 'org.mockito',
        }
        
        # Паттерны для внешних библиотек
        self.default_external_patterns = [
            r'^java\.',
            r'^javax\.',
            r'^kotlin\.',
            r'^kotlinx\.',
            r'^android\.',
            r'^androidx\.',
            r'^com\.google\.',
            r'^io\.', 
            r'^org\.',
        ]
    
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Kotlin import is external or local."""
        import re
        
        # Проверяем пользовательские паттерны
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Проверяем стандартные пакеты
        package_prefix = module_name.split('.')[0]
        if package_prefix in self.standard_packages:
            return True
        
        # Проверяем встроенные паттерны
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Эвристики для локальных импортов
        if self._is_local_import(module_name):
            return False
        
        # По умолчанию внешний
        return True
    
    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if import looks like a local/project import."""
        # Локальные паттерны (часто начинаются с имени проекта или специфичных префиксов)
        local_indicators = ['app', 'src', 'main', 'test', 'internal', 'impl']
        
        package_start = module_name.split('.')[0]
        return package_start in local_indicators


class KotlinImportAnalyzer(TreeSitterImportAnalyzer):
    """Kotlin-specific Tree-sitter import analyzer."""
    
    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Kotlin import using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1
        
        # В Kotlin импорты имеют тип import_header
        # import_header содержит identifier (путь импорта) и опциональный import_alias
        
        module_name = ""
        imported_items = []
        aliases = {}
        is_wildcard = False
        
        # Извлекаем путь импорта
        import_path_parts = []
        alias_name = None
        
        for child in node.children:
            if child.type == "identifier":
                # Собираем полный путь импорта (может быть составным)
                text = doc.get_node_text(child)
                import_path_parts.append(text)
            elif child.type == "import_alias":
                # Есть алиас для импорта (import ... as Alias)
                for alias_child in child.children:
                    if alias_child.type == "type_identifier":
                        alias_name = doc.get_node_text(alias_child)
        
        # Формируем полное имя модуля
        if import_path_parts:
            module_name = ".".join(import_path_parts)
        
        # Проверяем wildcard импорт (import java.util.*)
        if module_name.endswith(".*"):
            is_wildcard = True
            module_name = module_name[:-2]  # Убираем .*
            imported_items = ["*"]
        elif alias_name:
            imported_items = [alias_name]
            # Последняя часть пути - это импортируемый элемент
            if import_path_parts:
                actual_name = import_path_parts[-1]
                aliases[actual_name] = alias_name
        else:
            # Простой импорт без алиаса
            if import_path_parts:
                imported_items = [import_path_parts[-1]]
        
        return ImportInfo(
            node=node,
            import_type="import",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )


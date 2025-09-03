"""
Tree-sitter based Python adapter.
Replaces the existing python.py with enhanced Tree-sitter support.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from tree_sitter import Language, Parser

from .code_base import CodeAdapter
from .code_model import CodeCfg
from .import_utils import ImportClassifier, ImportAnalyzer, ImportInfo
from .range_edits import RangeEditor
from .tree_sitter_support import TreeSitterDocument, Node



@dataclass
class PythonCfg(CodeCfg):
    """Конфигурация для Python адаптера."""
    # Python-специфичные настройки
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1
    
    def __post_init__(self):
        # Устанавливаем Python-специфичные дефолты для плейсхолдеров
        if self.placeholders.template == "/* … {kind} {name} (−{lines}) */":
            self.placeholders.template = "# … {kind} {name} (−{lines})"
            self.placeholders.body_template = "# … body omitted (−{lines})"
            self.placeholders.import_template = "# … {count} imports omitted"
            self.placeholders.literal_template = "# … data omitted ({bytes} bytes)"


class PythonTreeSitterDocument(TreeSitterDocument):

    def get_language_parser(self) -> Parser:
        import tree_sitter_python as tspython
        return Parser(Language(tspython.language()))


class PythonTreeSitterAdapter(CodeAdapter[PythonCfg]):
    """Tree-sitter based Python adapter."""
    
    name = "python"
    extensions = {".py"}

    def should_skip(self, path: Path, text: str) -> bool:
        """
        Python-специфичные эвристики пропуска.
        Сохраняет логику для __init__.py из существующего адаптера.
        """
        if path.name == "__init__.py":
            # Проверяем на тривиальные __init__.py файлы
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
            
            # Используем конфигурацию (по умолчанию как в старом адаптере)
            # Получаем конфигурацию безопасно, если она не установлена - используем дефолты
            try:
                # Попытаемся получить конфигурацию
                cfg = self.cfg
                skip_trivial = cfg.skip_trivial_inits
                limit = cfg.trivial_init_max_noncomment
            except AttributeError:
                # Если конфигурация не установлена, используем дефолты
                skip_trivial = True
                limit = 1
            
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

        return super().should_skip(path, text)

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "#", ('"""', '"""')

    def create_document(text: str, ext: str) -> TreeSitterDocument:
        return PythonTreeSitterDocument(text, ext)

    def apply_tree_sitter_optimizations(
        self,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        meta: Dict[str, Any]
    ) -> None:
        """Python-специфичная обработка с Tree-sitter."""

        # Применяем базовую обработку функций
        if self.cfg.strip_function_bodies:
            self.strip_function_bodies_ts(doc, editor, meta)
            self._strip_python_methods(doc, editor, meta)

        # Применяем базовую обработку комментариев
        self.process_comments_ts(doc, editor, meta)

        # Применяем базовую обработку импортов
        self.process_imports_ts(doc, editor, meta)

        # TODO: добавить обработку декораторов, etc.
    
    def _create_import_classifier(self, external_patterns: List[str] = None):
        """Создает Python-специфичный классификатор импортов."""
        return PythonImportClassifier(external_patterns)
    
    def _create_import_analyzer(self, classifier):
        """Создает Python-специфичный анализатор импортов."""
        return PythonImportAnalyzer(classifier)
    
    def _strip_python_methods(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """Обрабатывает методы классов в Python."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Ищем методы в классах
        methods = doc.query("methods")
        processed_ranges = getattr(self, '_processed_ranges', set())
        
        for node, capture_name in methods:
            if capture_name == "method_body":
                # Получаем информацию о методе
                start_byte, end_byte = doc.get_node_range(node)
                
                # Пропускаем если этот диапазон уже обработан в базовом методе
                range_key = (start_byte, end_byte)
                if range_key in processed_ranges:
                    continue
                    
                method_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления
                should_strip = self._should_strip_function_body(cfg, method_text, lines_count)
                
                if should_strip:
                    # Для методов создаем другой плейсхолдер
                    placeholder = f"# … method body omitted (−{lines_count})"
                    
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="method_body_removal",
                        is_placeholder=True,
                        lines_removed=lines_count
                    )
                    
                    meta["code.removed.methods"] += 1


class PythonImportClassifier(ImportClassifier):
    """Python-specific import classifier."""
    
    def __init__(self, external_patterns: List[str] = None):
        self.external_patterns = external_patterns or []
        
        # Python standard library modules (partial list)
        self.python_stdlib = {
            'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
            'pathlib', 'collections', 'itertools', 'functools', 'typing',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
            'threading', 'multiprocessing', 'subprocess', 'logging',
            'unittest', 'argparse', 'configparser', 'shutil', 'glob',
            'pickle', 'base64', 'hashlib', 'hmac', 'secrets', 'uuid'
        }
        
        # Common external patterns
        self.default_external_patterns = [
            r'^[a-z][a-z0-9_]*$',  # Single word packages (numpy, pandas, etc.)
        ]
    
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Python module is external or local."""
        import re
        
        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Check if it's a Python standard library module
        base_module = module_name.split('.')[0]
        if base_module in self.python_stdlib:
            return True
        
        # Heuristics for local imports
        if self._is_local_import(module_name):
            return False
        
        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # If we can't determine, assume external for unknown packages
        return not self._looks_like_local(module_name)
    
    def _is_local_import(self, module_name: str) -> bool:
        """Check if import looks like a local/relative import."""
        import re
        
        # Relative imports
        if module_name.startswith('.'):
            return True
        
        # Common local patterns
        local_patterns = [
            r'^src\.',
            r'^lib\.',
            r'^utils\.',
            r'^models\.',
            r'^config\.',
            r'^tests?\.',
        ]
        
        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True
        
        return False
    
    def _looks_like_local(self, module_name: str) -> bool:
        """Heuristics to identify local modules."""
        import re
        
        # Contains uppercase (PascalCase, common in local modules)
        if any(c.isupper() for c in module_name):
            return True
        
        # Multiple dots often indicate deep local structure
        if module_name.count('.') >= 2:
            return True
        
        # Common local module patterns
        local_indicators = ['app', 'src', 'lib', 'utils', 'models', 'views', 'services', 'myapp']
        for indicator in local_indicators:
            if module_name.startswith(indicator + '.') or module_name == indicator:
                return True
        
        # Contains numbers or unusual underscores
        if re.search(r'[0-9]|__', module_name):
            return True
        
        return False


class PythonImportAnalyzer(ImportAnalyzer):
    """Python-specific import analyzer."""
    
    def _parse_import_node(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse a Python import node into ImportInfo."""
        import re
        
        import_text = doc.get_node_text(node)
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1
        
        if import_type == "import":
            # import os, sys, numpy as np
            match = re.match(r'import\s+(.+)', import_text)
            if match:
                imports_part = match.group(1)
                items = [item.strip() for item in imports_part.split(',')]
                
                # Extract module names and aliases
                module_names = []
                imported_items = []
                alias = None
                
                for item in items:
                    if ' as ' in item:
                        module, alias_part = item.split(' as ', 1)
                        module_names.append(module.strip())
                        imported_items.append(alias_part.strip())
                        alias = alias_part.strip()
                    else:
                        module_names.append(item.strip())
                        imported_items.append(item.strip())
                
                # Use first module for classification
                main_module = module_names[0] if module_names else ""
                
                return ImportInfo(
                    node=node,
                    import_type=import_type,
                    module_name=main_module,
                    imported_items=imported_items,
                    is_external=self.classifier.is_external(main_module),
                    alias=alias,
                    start_byte=start_byte,
                    end_byte=end_byte,
                    line_count=line_count
                )
        
        elif import_type == "import_from":
            # from os.path import join, dirname
            match = re.match(r'from\s+(.+?)\s+import\s+(.+)', import_text)
            if match:
                module_name = match.group(1).strip()
                imports_part = match.group(2).strip()
                
                # Parse imported items
                if imports_part == "*":
                    imported_items = ["*"]
                else:
                    items = [item.strip() for item in imports_part.split(',')]
                    imported_items = []
                    for item in items:
                        if ' as ' in item:
                            orig, alias = item.split(' as ', 1)
                            imported_items.append(f"{orig.strip()} as {alias.strip()}")
                        else:
                            imported_items.append(item)
                
                return ImportInfo(
                    node=node,
                    import_type=import_type,
                    module_name=module_name,
                    imported_items=imported_items,
                    is_external=self.classifier.is_external(module_name),
                    start_byte=start_byte,
                    end_byte=end_byte,
                    line_count=line_count
                )
        
        return None

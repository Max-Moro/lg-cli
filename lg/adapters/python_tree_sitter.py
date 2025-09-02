"""
Tree-sitter based Python adapter.
Replaces the existing python.py with enhanced Tree-sitter support.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

from .code_base import CodeAdapter, CodeDocument
from .code_model import CodeCfg
from .range_edits import RangeEditor
from .tree_sitter_support import TreeSitterDocument


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
        
        # TODO: добавить обработку декораторов, etc.
    
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

    # Совместимость со старым интерфейсом
    def parse_code(self, text: str) -> CodeDocument:
        """Совместимость - создает заглушку CodeDocument."""
        lines = text.splitlines()
        return CodeDocument(lines)

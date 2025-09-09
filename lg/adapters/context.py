"""
Контекст обработки для языковых адаптеров.
Инкапсулирует состояние и предоставляет методы для типовых операций.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional

from .metrics import MetricsCollector
from .placeholders import PlaceholderManager, create_placeholder_manager
from .range_edits import RangeEditor
from .tree_sitter_support import TreeSitterDocument, Node


class LightState:
    def __init__(
            self,
            file_path: Path,
            raw_text: str,
            group_size: int,
            mixed: bool
    ):
        self.file_path = file_path
        self.raw_text = raw_text
        self.group_size = group_size
        self.mixed = mixed

        # Вычисляем производные поля
        self.filename = file_path.name
        self.ext = file_path.suffix.lstrip(".") if file_path.suffix else ""

class LightweightContext(LightState):
    """
    Облегченный контекст обработки с базовой информацией о файле.
    Создается на раннем этапе и может быть ленивым образом расширен до ProcessingContext.
    """
    
    def __init__(
        self,
        file_path: Path,
        raw_text: str,
        group_size: int,
        mixed: bool
    ):
        super().__init__(file_path, raw_text, group_size, mixed)
        
        # Для ленивой инициализации полноценного контекста
        self._full_context: Optional['ProcessingContext'] = None

    def get_full_context(self, adapter) -> 'ProcessingContext':
        """
        Ленивое создание полноценного ProcessingContext при необходимости.
        
        Args:
            adapter: Языковой адаптер для создания документа и генератора плейсхолдеров
            
        Returns:
            ProcessingContext инициализированный из этого облегченного контекста
        """
        if self._full_context is None:
            self._full_context = ProcessingContext.from_lightweight(self, adapter)
        
        return self._full_context


class ProcessingContext(LightState):
    """
    Контекст обработки, инкапсулирующий doc, editor, placeholders и metrics.
    """
    
    def __init__(
        self,
        file_path: Path,
        raw_text: str,
        group_size: int,
        mixed: bool,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        placeholders: PlaceholderManager,
    ):
        super().__init__(file_path, raw_text, group_size, mixed)

        self.doc = doc
        self.editor = editor
        self.placeholders = placeholders
        self.metrics = MetricsCollector()

    # ============= API для плейсхолдеров =============
    
    def add_comment_placeholder(self, node: Node, is_docstring: bool = False, count: int = 1) -> None:
        """Добавить плейсхолдер для комментария/докстринга."""
        self.placeholders.add_comment_placeholder(node, self.doc, is_docstring=is_docstring, count=count)
        self.metrics.mark_comment_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_import_placeholder(self, node: Node, count: int = 1) -> None:
        """Добавить плейсхолдер для импорта."""
        self.placeholders.add_import_placeholder(node, self.doc, count=count)
        self.metrics.mark_import_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_literal_placeholder(self, node: Node, literal_type: str = "literal") -> None:
        """Добавить плейсхолдер для литерала."""
        self.placeholders.add_literal_placeholder(node, self.doc, literal_type=literal_type)
        self.metrics.mark_literal_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_custom_placeholder(self, start_byte: int, end_byte: int, start_line: int, end_line: int, 
                             placeholder_type: str, placeholder_prefix: str = "") -> None:
        """Добавить кастомный плейсхолдер."""
        self.placeholders.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line, placeholder_type, placeholder_prefix
        )
        self.metrics.mark_placeholder_inserted()
    
    # ============= Метод удаления без плейсхолдера =============
    
    def remove_range(self, start_byte: int, end_byte: int, **metadata) -> None:
        """Удалить диапазон без плейсхолдера."""
        self.editor.add_deletion(start_byte, end_byte, **metadata)
    
    def remove_node(self, node: Node, **metadata) -> None:
        """Удалить узел без плейсхолдера."""
        start_byte, end_byte = self.doc.get_node_range(node)
        self.editor.add_deletion(start_byte, end_byte, **metadata)

    def finalize(self) -> Dict[str, Any]:
        """
        Завершить обработку и получить финальные метрики.
        
        Returns:
            Словарь с полными метриками для включения в ProcessedBlob
        """
        # Финализируем плейсхолдеры и применяем их к редактору
        collapsed_edits, placeholder_stats = self.placeholders.finalize_edits()

        # Применяем все плейсхолдеры к редактору
        for spec, replacement_text in collapsed_edits:
            self.editor.add_replacement(
                spec.start_byte, spec.end_byte, replacement_text,
                type=f"{spec.placeholder_type}_placeholder",
                is_placeholder=(replacement_text != ""),
                lines_removed=spec.lines_removed
            )
        
        # Обновляем метрики из плейсхолдеров
        for key, value in placeholder_stats.items():
            if isinstance(value, (int, float)):
                self.metrics.set(key, value)
        
        # Добавляем метаданные группы
        self.metrics.set("_group_size", self.group_size)
        self.metrics.set("_group_mixed", self.mixed)

        return self.metrics.to_dict()

    @classmethod 
    def from_lightweight(
        cls,
        lightweight_ctx: LightweightContext,
        adapter
    ) -> 'ProcessingContext':
        """
        Создать полноценный ProcessingContext из облегченного контекста.
        
        Args:
            lightweight_ctx: Облегченный контекст с базовой информацией
            adapter: Языковой адаптер для создания компонентов
            
        Returns:
            Полноценный ProcessingContext
        """
        # Создаем компоненты для полноценного контекста
        doc = adapter.create_document(lightweight_ctx.raw_text, lightweight_ctx.ext)
        editor = RangeEditor(lightweight_ctx.raw_text)
        
        # Создаем PlaceholderManager с настройками из адаптера
        placeholders = create_placeholder_manager(
            lightweight_ctx.raw_text,
            adapter.get_comment_style(), 
            adapter.cfg.placeholders.style,
        )
        
        return cls(
            lightweight_ctx.file_path,
            lightweight_ctx.raw_text,
            lightweight_ctx.group_size,
            lightweight_ctx.mixed,
            doc,
            editor,
            placeholders
        )

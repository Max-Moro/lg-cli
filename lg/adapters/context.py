"""
Контекст обработки для языковых адаптеров.
Инкапсулирует состояние и предоставляет методы для типовых операций.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .metrics import MetricsCollector
from .range_edits import RangeEditor
from .placeholders import PlaceholderManager, create_placeholder_manager
from .tree_sitter_support import TreeSitterDocument, Node


class LightweightContext:
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
        self.file_path = file_path
        self.raw_text = raw_text
        self.group_size = group_size
        self.mixed = mixed
        
        # Вычисляем производные поля
        self.filename = file_path.name
        self.ext = file_path.suffix.lstrip(".") if file_path.suffix else ""
        
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


class ProcessingContext:
    """
    Контекст обработки, инкапсулирующий doc, editor, placeholders и metrics.
    """
    
    def __init__(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        placeholders: PlaceholderManager,
    ):
        self.doc = doc
        self.editor = editor
        self.placeholders = placeholders
        self.metrics = MetricsCollector()

    # ============= Удобное API для плейсхолдеров =============
    
    def add_function_placeholder(self, node: Node, **kwargs) -> None:
        """Добавить плейсхолдер для функции."""
        self.placeholders.add_function_placeholder(node, self.doc, **kwargs)
        self.metrics.mark_function_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_method_placeholder(self, node: Node, **kwargs) -> None:
        """Добавить плейсхолдер для метода."""
        self.placeholders.add_method_placeholder(node, self.doc, **kwargs)
        self.metrics.mark_method_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_comment_placeholder(self, node: Node, count: int = 1, **kwargs) -> None:
        """Добавить плейсхолдер для комментария."""
        self.placeholders.add_comment_placeholder(node, self.doc, count=count, **kwargs)
        self.metrics.mark_comment_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_import_placeholder(self, node: Node, count: int = 1, **kwargs) -> None:
        """Добавить плейсхолдер для импорта."""
        self.placeholders.add_import_placeholder(node, self.doc, count=count, **kwargs)
        self.metrics.mark_import_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_literal_placeholder(self, node: Node, literal_type: str = "literal", **kwargs) -> None:
        """Добавить плейсхолдер для литерала."""
        self.placeholders.add_literal_placeholder(node, self.doc, literal_type=literal_type, **kwargs)
        self.metrics.mark_literal_removed()
        self.metrics.mark_placeholder_inserted()
    
    def add_custom_placeholder(self, start_byte: int, end_byte: int, start_line: int, end_line: int, 
                             placeholder_type: str, **kwargs) -> None:
        """Добавить кастомный плейсхолдер."""
        self.placeholders.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line, placeholder_type, **kwargs
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

    def finalize(self, lightweight_ctx: Optional['LightweightContext'] = None, group_size: Optional[int] = None, mixed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Завершить обработку и получить финальные метрики.
        
        Args:
            lightweight_ctx: Облегченный контекст (приоритетный источник метаданных)
            group_size: Размер группы файлов (fallback если нет lightweight_ctx)
            mixed: Смешанные ли языки в группе (fallback если нет lightweight_ctx)
            
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
        
        # Извлекаем метаданные группы из контекста или используем переданные параметры
        if lightweight_ctx is not None:
            final_group_size = lightweight_ctx.group_size
            final_mixed = lightweight_ctx.mixed
        else:
            final_group_size = group_size or 1
            final_mixed = mixed or False
        
        # Добавляем метаданные группы
        self.metrics.set("_group_size", final_group_size)
        self.metrics.set("_group_mixed", final_mixed)

        return self.metrics.to_dict()

    @classmethod 
    def from_lightweight(
        cls,
        lightweight_ctx: 'LightweightContext',
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
        placeholder_style = adapter.cfg.placeholders.style if hasattr(adapter.cfg, 'placeholders') else "auto"
        placeholders = create_placeholder_manager(
            adapter.get_comment_style(), 
            placeholder_style
        )
        
        return cls(doc, editor, placeholders)

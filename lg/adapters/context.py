"""
Контекст обработки для языковых адаптеров.
Инкапсулирует состояние и предоставляет методы для типовых операций.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .metrics import MetricsCollector
from .range_edits import RangeEditor, PlaceholderGenerator
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
    Контекст обработки, инкапсулирующий doc, editor и metrics.
    """
    
    def __init__(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        placeholder_gen: PlaceholderGenerator,
    ):
        self.doc = doc
        self.editor = editor
        self.placeholder_gen = placeholder_gen
        self.metrics = MetricsCollector()

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
        placeholder_gen = PlaceholderGenerator(adapter.get_comment_style())
        
        return cls(doc, editor, placeholder_gen)

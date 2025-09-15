"""
Контекст обработки для языковых адаптеров.
Инкапсулирует состояние и предоставляет методы для типовых операций.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .metrics import MetricsCollector
from .placeholders import PlaceholderManager, create_placeholder_manager
from .range_edits import UnicodeRangeEditor
from .tree_sitter_support import TreeSitterDocument, Node
from ..stats import TokenService


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
        self._full_context: Optional[ProcessingContext] = None

    def get_full_context(self, adapter, tokenizer: TokenService) -> ProcessingContext:
        """
        Ленивое создание полноценного ProcessingContext при необходимости.
        
        Args:
            tokenizer: Сервис подсчёта токенов
            adapter: Языковой адаптер для создания документа и генератора плейсхолдеров
            
        Returns:
            ProcessingContext инициализированный из этого облегченного контекста
        """
        if self._full_context is None:
            self._full_context = ProcessingContext.from_lightweight(self, adapter, tokenizer)
        
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
        adapter_name: str,
        doc: TreeSitterDocument,
        editor: UnicodeRangeEditor,
        placeholders: PlaceholderManager,
        tokenizer: TokenService,
    ):
        super().__init__(file_path, raw_text, group_size, mixed)

        self.doc = doc
        self.editor = editor
        self.placeholders = placeholders
        self.metrics = MetricsCollector(adapter_name)
        self.tokenizer = tokenizer

    def add_placeholder(self, element_type: str, start_char: int, end_char: int, start_line: int, end_line: int,
                        placeholder_prefix: str = "", count: int = 1) -> None:
        """Добавить плейсхолдер."""
        self.placeholders.add_placeholder(
            element_type, start_char, end_char, start_line, end_line, placeholder_prefix, count
        )
        self.metrics.mark_element_removed(element_type, count)
        self.metrics.mark_placeholder_inserted()

    def add_placeholder_for_node(self, element_type: str, node: Node, count: int = 1) -> None:
        """Добавить плейсхолдер ровно по границам ноды."""
        self.placeholders.add_placeholder_for_node(element_type, node, self.doc, count=count)
        self.metrics.mark_element_removed(element_type, count)
        self.metrics.mark_placeholder_inserted()

    @classmethod
    def from_lightweight(
        cls,
        lightweight_ctx: LightweightContext,
        adapter,
        tokenizer: TokenService
    ) -> ProcessingContext:
        """
        Создать полноценный ProcessingContext из облегченного контекста.
        
        Args:
            lightweight_ctx: Облегченный контекст с базовой информацией
            adapter: Языковой адаптер для создания компонентов
            tokenizer: Cервис подсчёта токенов

        Returns:
            Полноценный ProcessingContext
        """
        # Создаем компоненты для полноценного контекста
        doc = adapter.create_document(lightweight_ctx.raw_text, lightweight_ctx.ext)
        editor = UnicodeRangeEditor(lightweight_ctx.raw_text)
        
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
            adapter.name,
            doc,
            editor,
            placeholders,
            tokenizer,
        )

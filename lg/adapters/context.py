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
from ..tokens.service import TokenService


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
        token_service: TokenService,
        placeholder_min_ratio: float,
        placeholder_min_abs_if_none: Optional[int],
    ):
        super().__init__(file_path, raw_text, group_size, mixed)

        self.doc = doc
        self.editor = editor
        self.placeholders = placeholders
        self.metrics = MetricsCollector()
        self.token_service = token_service
        self.placeholder_min_ratio = placeholder_min_ratio
        self.placeholder_min_abs_if_none = placeholder_min_abs_if_none

    # ============= API для плейсхолдеров =============

    def add_placeholder(self, element_type: str, start_byte: int, end_byte: int, start_line: int, end_line: int,
                        placeholder_prefix: str = "", count: int = 1) -> None:
        """Добавить плейсхолдер."""
        self.placeholders.add_placeholder(
            element_type, start_byte, end_byte, start_line, end_line, placeholder_prefix, count
        )
        self.metrics.mark_element_removed(element_type, count)
        self.metrics.mark_placeholder_inserted()

    def add_placeholder_for_node(self, element_type: str, node: Node, count: int = 1) -> None:
        """Добавить плейсхолдер ровно по границам ноды."""
        self.placeholders.add_placeholder_for_node(element_type, node, self.doc, count=count)
        self.metrics.mark_element_removed(element_type, count)
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

        # Применяем экономическую проверку перед внесением замен

        # Применяем все плейсхолдеры к редактору
        # Текст исходного диапазона нужен для экономической проверки
        original_bytes = self.raw_text.encode('utf-8')

        min_savings_ratio = self.placeholder_min_ratio
        min_abs_savings_if_none = self.placeholder_min_abs_if_none

        for spec, replacement_text in collapsed_edits:
            # Получаем исходный текст диапазона
            src = original_bytes[spec.start_byte:spec.end_byte].decode('utf-8', errors='ignore')
            repl = replacement_text

            # Определяем флаг "пустой" замены
            is_none = (repl == "")

            # Применяем проверку целесообразности
            # Если сервис не задан — применяем вслепую (как раньше)
            if self.token_service:
                if not self.token_service.is_economical(
                    src,
                    repl,
                    min_ratio=min_savings_ratio,
                    replacement_is_none=is_none,
                    min_abs_savings_if_none=min_abs_savings_if_none,
                ):
                    # Пропускаем замену, оставляем оригинал
                    continue

            self.editor.add_replacement(
                spec.start_byte, spec.end_byte, repl,
                type=f"{spec.placeholder_type}_placeholder",
                is_placeholder=(repl != ""),
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
        # Сервис токенов передаёт engine при связывании адаптера
        token_service = getattr(adapter, 'token_service', None)

        # Параметры экономической проверки из конфигурации адаптера
        ph_cfg = getattr(adapter.cfg, 'placeholders', None)
        min_ratio = getattr(ph_cfg, 'min_savings_ratio', 2.0) if ph_cfg else 2.0
        min_abs_if_none = getattr(ph_cfg, 'min_abs_savings_if_none', None) if ph_cfg else None
        
        return cls(
            lightweight_ctx.file_path,
            lightweight_ctx.raw_text,
            lightweight_ctx.group_size,
            lightweight_ctx.mixed,
            doc,
            editor,
            placeholders,
            token_service,
            min_ratio,
            min_abs_if_none,
        )

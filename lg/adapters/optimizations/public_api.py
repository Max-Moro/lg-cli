"""
Public API optimization.
Filters code to show only public/exported elements.
"""

from __future__ import annotations

from typing import cast

from ..context import ProcessingContext


class PublicApiOptimizer:
    """Handles filtering code for public API only."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply public API filtering.
        Removes private/protected elements, keeping only public/exported ones.
        
        Args:
            context: Processing context with document and editor
        """
        # Получаем унифицированный анализатор кода для языка
        code_analyzer = self.adapter.create_code_analyzer(context.doc)
        
        # Собираем все приватные элементы с помощью анализатора
        private_elements = code_analyzer.collect_private_elements_for_public_api()
        
        # Сначала вычисляем диапазоны с декораторами для всех элементов
        element_ranges = [
            (code_analyzer.get_element_range_with_decorators(elem), elem)
            for elem in private_elements
        ]
        
        # Сортируем по позиции (в обратном порядке для безопасного удаления)
        element_ranges.sort(key=lambda x: x[0][0], reverse=True)
        
        # Удаляем приватные элементы с соответствующими плейсхолдерами
        for (start_byte, end_byte), private_element in element_ranges:
            start_line = context.doc.get_line_number_for_byte(start_byte)
            end_line = context.doc.get_line_number_for_byte(end_byte)
            context.add_placeholder(private_element.element_type, start_byte, end_byte, start_line, end_line)

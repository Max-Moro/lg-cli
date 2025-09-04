"""
Контекст обработки для языковых адаптеров.
Инкапсулирует состояние и предоставляет удобные методы для типовых операций.
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
    
    # ============= Методы для типовых операций =============
    
    def remove_function_body(
        self, 
        body_node: Node, 
        func_type: str = "function",
        placeholder_style: str = "inline"
    ) -> bool:
        """
        Удаляет тело функции/метода с автоматическим учетом метрик.
        
        Returns:
            True если удаление было выполнено, False если пропущено
        """
        start_byte, end_byte = self.doc.get_node_range(body_node)
        start_line, end_line = self.doc.get_line_range(body_node)
        lines_count = end_line - start_line + 1
        
        # Создаем плейсхолдер в зависимости от типа
        if func_type == "method":
            placeholder = self.placeholder_gen.create_method_placeholder(
                lines_removed=lines_count,
                bytes_removed=end_byte - start_byte,
                style=placeholder_style
            )
            self.metrics.mark_method_removed()
        else:
            placeholder = self.placeholder_gen.create_function_placeholder(
                lines_removed=lines_count,
                bytes_removed=end_byte - start_byte,
                style=placeholder_style
            )
            self.metrics.mark_function_removed()
        
        # Добавляем правку
        self.editor.add_replacement(
            start_byte, end_byte, placeholder,
            type=f"{func_type}_body_removal",
            is_placeholder=True,
            lines_removed=lines_count
        )
        
        self.metrics.add_lines_saved(lines_count)
        self.metrics.add_bytes_saved(end_byte - start_byte - len(placeholder.encode('utf-8')))
        self.metrics.mark_placeholder_inserted()
        
        return True
    
    def remove_comment(
        self,
        comment_node: Node,
        comment_type: str = "comment",
        replacement: str = None,
        placeholder_style: str = "inline"
    ) -> bool:
        """
        Удаляет комментарий с автоматическим учетом метрик.
        
        Args:
            comment_node: Узел комментария для удаления
            comment_type: Тип комментария ("comment", "docstring")
            replacement: Кастомная замена (если None, используется плейсхолдер)
            placeholder_style: Стиль плейсхолдера
            
        Returns:
            True если удаление было выполнено
        """
        start_byte, end_byte = self.doc.get_node_range(comment_node)
        start_line, end_line = self.doc.get_line_range(comment_node)
        lines_count = end_line - start_line + 1
        
        if replacement is None:
            replacement = self.placeholder_gen.create_comment_placeholder(
                comment_type, style=placeholder_style
            )
            self.metrics.mark_placeholder_inserted()
        
        self.editor.add_replacement(
            start_byte, end_byte, replacement,
            type=f"{comment_type}_removal",
            is_placeholder=bool(replacement),
            lines_removed=lines_count
        )
        
        self.metrics.mark_comment_removed()
        if replacement:
            self.metrics.add_lines_saved(lines_count)
            bytes_saved = end_byte - start_byte - len(replacement.encode('utf-8'))
            if bytes_saved > 0:
                self.metrics.add_bytes_saved(bytes_saved)
        
        return True
    
    def remove_import(
        self,
        import_node: Node,
        import_type: str = "import",
        placeholder_style: str = "inline"
    ) -> bool:
        """
        Удаляет импорт с автоматическим учетом метрик.
        """
        start_byte, end_byte = self.doc.get_node_range(import_node)
        start_line, end_line = self.doc.get_line_range(import_node)
        lines_count = end_line - start_line + 1
        
        placeholder = self.placeholder_gen.create_import_placeholder(
            count=1, style=placeholder_style
        )
        
        self.editor.add_replacement(
            start_byte, end_byte, placeholder,
            type=f"{import_type}_removal",
            is_placeholder=True,
            lines_removed=lines_count
        )
        
        self.metrics.mark_import_removed()
        self.metrics.add_lines_saved(lines_count)
        self.metrics.add_bytes_saved(end_byte - start_byte - len(placeholder.encode('utf-8')))
        self.metrics.mark_placeholder_inserted()
        
        return True
    
    def is_method(self, function_body_node: Node) -> bool:
        """
        Определяет, является ли узел function_body методом класса.
        Проходит вверх по дереву в поисках class_definition или class_declaration.
        """
        current = function_body_node.parent
        while current:
            if current.type in ("class_definition", "class_declaration"):
                return True
            current = current.parent
        return False
    
    # ============= Методы для работы с группами элементов =============
    
    def remove_consecutive_imports(
        self,
        import_ranges: list,
        group_type: str,
        placeholder_style: str = "inline"
    ) -> None:
        """
        Удаляет группу последовательных импортов с единым плейсхолдером.
        """
        if not import_ranges:
            return
        
        # Получаем диапазон всей группы
        start_byte = import_ranges[0][0]
        end_byte = import_ranges[-1][1]
        
        # Создаем суммарный плейсхолдер
        count = len(import_ranges)
        summary = f"… {count} {group_type} imports"
        
        if placeholder_style == "block":
            placeholder = self.placeholder_gen.create_custom_placeholder(
                summary, {}, style="block"
            )
        else:
            placeholder = f"# {summary}"
        
        total_lines = sum(imp[2].line_count for imp in import_ranges)
        
        self.editor.add_replacement(
            start_byte, end_byte, placeholder,
            type="import_summarization",
            is_placeholder=True,
            lines_removed=total_lines
        )
        
        # Обновляем метрики
        for _ in import_ranges:
            self.metrics.mark_import_removed()
        
        self.metrics.add_lines_saved(total_lines)
        self.metrics.mark_placeholder_inserted()
    
    # ============= Методы для доступа к данным =============
    
    def get_node_text(self, node: Node) -> str:
        """Получить текст узла (делегирует к doc)."""
        return self.doc.get_node_text(node)
    
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """Получить байтовый диапазон узла."""
        return self.doc.get_node_range(node)
    
    def get_line_range(self, node: Node) -> Tuple[int, int]:
        """Получить диапазон строк узла."""
        return self.doc.get_line_range(node)
    
    def query(self, query_name: str):
        """Выполнить запрос к документу."""
        return self.doc.query(query_name)
    
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


# ===== TEST UTILITIES ===== #

def create_test_lightweight_context(
    raw_text: str = "# Test content",
    filename: str = "test.py",
    group_size: int = 1,
    mixed: bool = False
) -> LightweightContext:
    """
    Создает stub LightweightContext для тестов.
    
    Args:
        raw_text: Содержимое файла
        filename: Имя файла
        group_size: Размер группы
        mixed: Смешанные языки
        
    Returns:
        LightweightContext для использования в тестах
    """
    test_path = Path(filename)
    return LightweightContext(
        file_path=test_path,
        raw_text=raw_text,
        group_size=group_size,
        mixed=mixed
    )

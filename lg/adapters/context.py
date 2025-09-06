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
    
    def remove_function_body_preserve_docstring(
        self,
        body_node: Node,
        func_type: str = "function",
        placeholder_style: str = "inline"
    ) -> bool:
        """
        Удаляет тело функции/метода, сохраняя docstring, если он есть.
        
        Args:
            body_node: Узел тела функции
            func_type: Тип функции ("function" или "method")
            placeholder_style: Стиль плейсхолдера
            
        Returns:
            True если удаление было выполнено
        """
        # Ищем docstring в теле функции
        docstring_node = self._find_docstring_in_body(body_node)
        
        if docstring_node is None:
            # Нет docstring - удаляем всё содержимое после ':' в определении функции
            return self._remove_function_body_complete(body_node, func_type, placeholder_style)
        
        # Есть docstring - удаляем только часть после него
        docstring_end_byte = docstring_node.end_byte
        body_start_byte, body_end_byte = self.doc.get_node_range(body_node)
        
        # Найдём первый символ после docstring (обычно перевод строки)
        # Нужно найти следующий statement после docstring
        next_statement_start = self._find_next_statement_after_docstring(body_node, docstring_node)
        
        if next_statement_start is None or next_statement_start >= body_end_byte:
            # Нет кода после docstring - оставляем только docstring
            return False
        
        # Вычисляем что удаляем (от начала следующего statement до конца тела)
        removal_start = next_statement_start
        removal_end = body_end_byte
        
        # Подсчитываем статистику
        removal_start_line = self._get_line_number_for_byte(removal_start)
        body_end_line = self.doc.get_line_range(body_node)[1] 
        lines_removed = max(0, body_end_line - removal_start_line + 1)
        
        if lines_removed <= 0:
            # Нечего удалять после docstring
            return False
        
        # Создаем плейсхолдер
        if func_type == "method":
            placeholder = self.placeholder_gen.create_method_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            self.metrics.mark_method_removed()
        else:
            placeholder = self.placeholder_gen.create_function_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            self.metrics.mark_function_removed()
        
        # Добавляем правку (заменяем код после docstring на плейсхолдер)
        self.editor.add_replacement(
            removal_start, removal_end, f"\n    {placeholder}",
            type=f"{func_type}_body_removal_preserve_docstring",
            is_placeholder=True,
            lines_removed=lines_removed
        )
        
        self.metrics.add_lines_saved(lines_removed)
        bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
        if bytes_saved > 0:
            self.metrics.add_bytes_saved(bytes_saved)
        self.metrics.mark_placeholder_inserted()
        
        return True
    
    def _find_next_statement_after_docstring(self, body_node: Node, docstring_node: Node) -> Optional[int]:
        """
        Находит начальный байт следующего statement после docstring.
        """
        docstring_found = False
        for child in body_node.children:
            if docstring_found:
                # Нашли следующий statement после docstring
                return child.start_byte
            if child == docstring_node:
                docstring_found = True
        
        return None
    
    def _get_line_number_for_byte(self, byte_offset: int) -> int:
        """
        Получает номер строки (0-based) для байтового смещения.
        """
        # Простая реализация - подсчитываем переводы строк до этого байта
        text_before = self.doc._text_bytes[:byte_offset]
        return text_before.count(b'\n')
    
    def _remove_function_body_complete(
        self,
        body_node: Node,
        func_type: str = "function",
        placeholder_style: str = "inline"
    ) -> bool:
        """
        Полностью удаляет тело функции, включая комментарии и всё содержимое.
        Используется когда нет docstring для сохранения.
        """
        # Найдём функцию-родителя
        function_node = self._find_function_definition(body_node)
        if function_node is None:
            # Fallback к обычному удалению body_node
            return self.remove_function_body(body_node, func_type, placeholder_style)
        
        # Найдём позицию ':' в определении функции
        function_text = self.doc.get_node_text(function_node)
        colon_index = function_text.find(':')
        if colon_index == -1:
            # Fallback если не нашли ':'
            return self.remove_function_body(body_node, func_type, placeholder_style)
        
        # Вычисляем диапазон удаления: от ':' + 1 до конца функции
        function_start_byte = function_node.start_byte
        removal_start = function_start_byte + colon_index + 1
        removal_end = function_node.end_byte
        
        # Подсчитываем статистику
        removal_start_line = self._get_line_number_for_byte(removal_start)
        function_end_line = self.doc.get_line_range(function_node)[1]
        lines_removed = max(0, function_end_line - removal_start_line + 1)
        
        if lines_removed <= 0:
            return False
        
        # Создаем плейсхолдер
        if func_type == "method":
            placeholder = self.placeholder_gen.create_method_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            self.metrics.mark_method_removed()
        else:
            placeholder = self.placeholder_gen.create_function_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            self.metrics.mark_function_removed()
        
        # Заменяем всё содержимое после ':' на плейсхолдер
        self.editor.add_replacement(
            removal_start, removal_end, f"\n    {placeholder}",
            type=f"{func_type}_body_complete_removal",
            is_placeholder=True,
            lines_removed=lines_removed
        )
        
        self.metrics.add_lines_saved(lines_removed)
        bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
        if bytes_saved > 0:
            self.metrics.add_bytes_saved(bytes_saved)
        self.metrics.mark_placeholder_inserted()
        
        return True
    
    def _find_function_definition(self, body_node: Node) -> Optional[Node]:
        """
        Находит узел function_definition для данного body узла.
        """
        current = body_node.parent
        while current:
            if current.type in ("function_definition", "method_definition"):
                return current
            current = current.parent
        return None
    
    def _find_docstring_in_body(self, body_node: Node) -> Optional[Node]:
        """
        Находит docstring в теле функции (первый expression_statement со string).
        
        Args:
            body_node: Узел тела функции
            
        Returns:
            Узел docstring или None если не найден
        """
        # Ищем первый statement в теле
        for child in body_node.children:
            if child.type == "expression_statement":
                # Ищем string внутри expression_statement
                for expr_child in child.children:
                    if expr_child.type == "string":
                        return child  # Возвращаем весь expression_statement
                # Если первый expression_statement не содержит string, это не docstring
                break
        
        return None
    
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

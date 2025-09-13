"""
Централизованная система управления плейсхолдерами для языковых адаптеров.
Предоставляет унифицированное API и умное коллапсирование плейсхолдеров.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from .tree_sitter_support import Node


@dataclass
class PlaceholderSpec:
    """
    Спецификация плейсхолдера с метаданными.
    Хранит структурированную информацию о плейсхолдере без привязки к конкретному формату.
    """
    # Позиция в файле
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    
    # Тип плейсхолдера
    placeholder_type: str  # "function_body", "method_body", "import", "comment", "literal", etc.

    # Выравнивание плейсхолдера (табуляция)
    placeholder_prefix: str = ""
    
    # Метрики
    lines_removed: int = 0
    bytes_removed: int = 0
    count: int = 1  # Количество элементов (для импортов, комментариев)
    
    def __post_init__(self):
        # Вычисляем метрики если не переданы
        if self.lines_removed == 0:
            self.lines_removed = max(0, self.end_line - self.start_line + 1)
        if self.bytes_removed == 0:
            self.bytes_removed = max(0, self.end_byte - self.start_byte)
    
    @property
    def position_key(self) -> Tuple[int, int]:
        """Ключ для сортировки по позиции."""
        return self.start_line, self.start_byte
    
    def can_merge_with(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Проверяет, можно ли объединить этот плейсхолдер с другим.
        
        Условия объединения:
        - Одинаковый тип плейсхолдера
        - Подходящие типы
        - Отсутствие значимого контента между плейсхолдерами
        """
        if self.placeholder_type != other.placeholder_type:
            return False

        # Коллапсировать плейсхолдеры можно для импортов, комментариев, функций, методов, классов, интерфейсов и типов целиком.
        # Нельзя коллапсировать плейсхолдеры для литералов, тел функций или методов, докстрингов.
        if self.placeholder_type in ["function_body", "method_body", "docstring", "string", "array", "object", "literal"]:
            return False
        
        # Проверяем содержимое между плейсхолдерами
        return not self._has_significant_content_between(other, source_text)

    def _has_significant_content_between(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Консервативная проверка значимого контента между плейсхолдерами.
        
        Использует строгий подход: плейсхолдеры объединяются только если между ними
        действительно нет никакого кода - только пустые строки, пробелы и табуляции.
        Также проверяет, что плейсхолдеры имеют одинаковое количество символов от начала строки.

        Args:
            other: Другой плейсхолдер для сравнения
            source_text: Исходный текст документа

        Returns:
            True если между плейсхолдерами есть любой код или разное количество символов от начала строки, False если только пустота и одинаковые отступы
        """
        bytes_data = source_text.encode('utf-8')

        # Определяем диапазон между плейсхолдерами
        if self.end_byte <= other.start_byte:
            # self идет перед other
            start_byte = self.end_byte
            end_byte = other.start_byte
        elif other.end_byte <= self.start_byte:
            # other идет перед self
            start_byte = other.end_byte
            end_byte = self.start_byte
        else:
            # Плейсхолдеры пересекаются - можно объединять
            return False

        # Получаем содержимое между плейсхолдерами в байтах
        if start_byte >= end_byte:
            return False

        try:
            content_between = bytes_data[start_byte:end_byte].decode('utf-8')
        except (UnicodeDecodeError, IndexError):
            # При ошибках декодирования консервативно блокируем объединение
            return True

        # Консервативный подход: любой непустой контент блокирует объединение
        stripped = content_between.strip()
        if stripped:
            return True

        # Проверяем количество символов от начала строки для каждого плейсхолдера
        self_chars_from_line_start = self._count_chars_from_line_start(self.start_byte, source_text)
        other_chars_from_line_start = self._count_chars_from_line_start(other.start_byte, source_text)

        if self_chars_from_line_start != other_chars_from_line_start:
            return True

        return False

    def _count_chars_from_line_start(self, byte_position: int, source_text: str) -> int:
        """
        Считает количество символов от начала строки до указанной байтовой позиции.

        Args:
            byte_position: Байтовая позиция в тексте
            source_text: Исходный текст документа

        Returns:
            Количество символов от ближайшего '\n' слева до позиции
        """
        # Идем влево от позиции и ищем ближайший '\n'
        for i in range(byte_position - 1, -1, -1):
            if i < len(source_text) and source_text[i] == '\n':
                # Нашли '\n', считаем символы от него до позиции
                return byte_position - i - 1

        # Если '\n' не найден, значит мы в начале файла
        return byte_position
    
    def merge_with(self, other: PlaceholderSpec, source_text) -> PlaceholderSpec:
        """Создает объединенный плейсхолдер."""
        if not self.can_merge_with(other, source_text):
            raise ValueError("Cannot merge incompatible placeholders")
        
        # Объединенные границы
        start_byte = min(self.start_byte, other.start_byte)
        end_byte = max(self.end_byte, other.end_byte)
        start_line = min(self.start_line, other.start_line)
        end_line = max(self.end_line, other.end_line)
        
        return PlaceholderSpec(
            start_byte=start_byte,
            end_byte=end_byte,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=self.placeholder_type,
            placeholder_prefix=self.placeholder_prefix,
            lines_removed=self.lines_removed + other.lines_removed,
            bytes_removed=self.bytes_removed + other.bytes_removed,
            count=self.count + other.count,
        )


@dataclass
class CommentStyle:
    """Стиль комментариев для языка."""
    single_line: str  # "#", "//", etc.
    multi_line_start: str  # "/*", '"""', etc.
    multi_line_end: str   # "*/", '"""', etc.
    docstring_start: str
    docstring_end: str


class PlaceholderManager:
    """
    Центральный менеджер для управления плейсхолдерами.
    Предоставляет унифицированное API и обрабатывает коллапсирование.
    """
    
    def __init__(self, raw_text: str, comment_style: CommentStyle, placeholder_style: str):
        self.raw_text = raw_text
        self.comment_style = comment_style
        self.placeholder_style = placeholder_style
        self.placeholders: List[PlaceholderSpec] = []
        self._pending_edits: List[Tuple[PlaceholderSpec, str]] = []  # (spec, replacement_text)
    
    # ============= Простое API для добавления плейсхолдеров =============
    
    def add_placeholder(self, placeholder_type: str, start_byte: int, end_byte: int, start_line: int, end_line: int,
                        placeholder_prefix: str = "", count: int = 1) -> None:
        """Добавить кастомный плейсхолдер с явными координатами."""
        spec = PlaceholderSpec(
            start_byte=start_byte,
            end_byte=end_byte,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=placeholder_type,
            placeholder_prefix=placeholder_prefix,
            count=count,
        )
        self._add_placeholder(spec)

    def add_placeholder_for_node(self, placeholder_type: str, node: Node, doc, count: int = 1) -> None:
        """Добавить плейсхолдер для импорта."""
        spec = self._create_spec_from_node(node, doc, placeholder_type, count=count)
        self._add_placeholder(spec)
    
    # ============= Внутренние методы =============
    
    def _create_spec_from_node(self, node: Node, doc, placeholder_type: str, count: int = 1) -> PlaceholderSpec:
        """Создать PlaceholderSpec из Tree-sitter узла."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        
        return PlaceholderSpec(
            start_byte=start_byte,
            end_byte=end_byte,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=placeholder_type,
            placeholder_prefix="",
            count=count,
        )
    
    def _add_placeholder(self, spec: PlaceholderSpec) -> None:
        """Добавить плейсхолдер в список."""
        # Обрабатываем стиль "none" - полное удаление без плейсхолдера
        if self.placeholder_style == "none":
            self._pending_edits.append((spec, ""))
            return
        
        # Генерируем текст плейсхолдера
        placeholder_text = self._generate_placeholder_text(spec)
        self._pending_edits.append((spec, placeholder_text))
        
        # Добавляем в список для потенциального коллапсирования
        self.placeholders.append(spec)
    
    def _generate_placeholder_text(self, spec: PlaceholderSpec) -> str:
        """Генерировать текст плейсхолдера на основе типа и стиля."""
        content = self._get_placeholder_content(spec)
        
        # Для докстрингов всегда используем родное обрамление языка
        if spec.placeholder_type == "docstring":
            return f"{spec.placeholder_prefix}{self.comment_style.docstring_start} {content} {self.comment_style.docstring_end}"
        
        # Стандартная логика для обычных комментариев
        if self.placeholder_style == "inline":
            return f"{spec.placeholder_prefix}{self.comment_style.single_line} {content}"
        else: # self.placeholder_style == "block"
            return f"{spec.placeholder_prefix}{self.comment_style.multi_line_start} {content} {self.comment_style.multi_line_end}"
    
    def _get_placeholder_content(self, spec: PlaceholderSpec) -> str:
        """Сгенерировать содержимое плейсхолдера на основе типа и метрик."""
        ptype = spec.placeholder_type
        count = spec.count
        lines = spec.lines_removed
        bytes_removed = spec.bytes_removed
        
        # Базовые шаблоны для разных типов
        if ptype == "function_body":
            if lines > 1:
                return f"… function body omitted ({lines} lines)"
            else:
                return "… function body omitted"
        
        elif ptype == "method_body":
            if lines > 1:
                return f"… method body omitted ({lines} lines)"
            else:
                return "… method body omitted"
        
        elif ptype == "comment":
            if count > 1:
                return f"… {count} comments omitted"
            else:
                return "… comment omitted"

        elif ptype == "docstring":
            return "… docstring omitted"
        
        elif ptype == "import":
            if count > 1:
                return f"… {count} imports omitted"
            else:
                return "… import omitted"
        
        elif ptype == "function":
            if count > 1:
                return f"… {count} functions omitted"
            else:
                return "… function omitted"
        
        elif ptype == "method":
            if count > 1:
                return f"… {count} methods omitted"
            else:
                return "… method omitted"
        
        elif ptype == "class":
            if count > 1:
                return f"… {count} classes omitted"
            else:
                return "… class omitted"
        
        elif ptype == "interface":
            if count > 1:
                return f"… {count} interfaces omitted"
            else:
                return "… interface omitted"
        
        elif ptype == "type":
            if count > 1:
                return f"… {count} types omitted"
            else:
                return "… type omitted"
        
        elif ptype in ("string", "array", "object", "literal"):
            if bytes_removed > 0:
                return f"… {ptype} data omitted ({bytes_removed} bytes)"
            else:
                return f"… {ptype} omitted"
        
        else:
            # Универсальный шаблон для неизвестных типов
            if count > 1:
                return f"… {count} {ptype}s omitted"
            elif lines > 1:
                return f"… {ptype} omitted ({lines} lines)"
            else:
                return f"… {ptype} omitted"
    
    # ============= Коллапсирование и финализация =============

    def raw_edits(self) -> List[PlaceholderSpec]:
        """
        Возвращаем сырые правки для оценки в системе бюджета.
        """
        return [edit for edit, _ in self._pending_edits]

    def finalize_edits(self) -> Tuple[List[Tuple[PlaceholderSpec, str]], Dict[str, Any]]:
        """
        Финализировать все правки с коллапсированием.

        Returns:
            (collapsed_edits, stats)
        """
        if self.placeholder_style == "none":
            edits = self._pending_edits

            # Собираем статистику
            stats = self._calculate_stats(edits)

            return edits, stats

        # Выполняем коллапсирование плейсхолдеров
        collapsed_specs = self._collapse_placeholders()

        # Обновляем правки на основе коллапсированных плейсхолдеров
        collapsed_edits = self._update_edits_with_collapsed(collapsed_specs)

        # Собираем статистику
        stats = self._calculate_stats(collapsed_edits)

        return collapsed_edits, stats

    def _collapse_placeholders(self) -> List[PlaceholderSpec]:
        """
        Коллапсировать соседние плейсхолдеры одного типа.
        Работает на уровне данных, без парсинга текста.
        """
        if not self.placeholders:
            return []

        # Сортируем по позиции
        sorted_placeholders = sorted(self.placeholders, key=lambda p: p.position_key)

        collapsed = []
        current_group = [sorted_placeholders[0]]

        for placeholder in sorted_placeholders[1:]:
            # Проверяем, можно ли объединить с текущей группой
            if current_group and current_group[-1].can_merge_with(placeholder, self.raw_text):
                current_group.append(placeholder)
            else:
                # Финализируем текущую группу
                collapsed.append(self._merge_group(current_group))
                current_group = [placeholder]

        # Не забываем последнюю группу
        if current_group:
            collapsed.append(self._merge_group(current_group))

        return collapsed

    def _merge_group(self, group: List[PlaceholderSpec]) -> PlaceholderSpec:
        """Объединить группу плейсхолдеров в один."""
        if len(group) == 1:
            return group[0]

        # Последовательно объединяем все плейсхолдеры в группе
        result = group[0]
        for placeholder in group[1:]:
            result = result.merge_with(placeholder, self.raw_text)

        return result
    
    def _update_edits_with_collapsed(self, collapsed_specs: List[PlaceholderSpec]) -> List[Tuple[PlaceholderSpec, str]]:
        """Обновить список правок на основе коллапсированных плейсхолдеров."""
        # Создаем карту spec -> replacement_text из оригинальных правок
        original_map = {id(spec): replacement for spec, replacement in self._pending_edits}
        
        updated_edits = []
        
        for collapsed_spec in collapsed_specs:
            # Для коллапсированных плейсхолдеров генерируем новый текст
            if collapsed_spec.count > 1:  # Это результат объединения
                replacement_text = self._generate_placeholder_text(collapsed_spec)
            else:
                # Пытаемся найти оригинальный текст
                replacement_text = None
                for spec, replacement in self._pending_edits:
                    if (spec.start_byte == collapsed_spec.start_byte and 
                        spec.end_byte == collapsed_spec.end_byte):
                        replacement_text = replacement
                        break
                
                # Если не найден, генерируем заново
                if replacement_text is None:
                    replacement_text = self._generate_placeholder_text(collapsed_spec)
            
            updated_edits.append((collapsed_spec, replacement_text))
        
        return updated_edits
    
    def _calculate_stats(self, edits: List[Tuple[PlaceholderSpec, str]]) -> Dict[str, Any]:
        """Вычислить статистику плейсхолдеров."""
        stats = {
            "placeholders_inserted": len(edits),
            "total_lines_removed": sum(spec.lines_removed for spec, _ in edits),
            "total_bytes_removed": sum(spec.bytes_removed for spec, _ in edits),
            "placeholders_by_type": {}
        }
        
        # Группируем по типам
        for spec, _ in edits:
            ptype = spec.placeholder_type
            if ptype not in stats["placeholders_by_type"]:
                stats["placeholders_by_type"][ptype] = 0
            stats["placeholders_by_type"][ptype] += spec.count
        
        return stats


# ============= Фабричные функции =============

def create_placeholder_manager(
    raw_text: str, 
    comment_style_tuple: Tuple[str, Tuple[str, str], Tuple[str, str]],
    placeholder_style: str
) -> PlaceholderManager:
    """
    Создать PlaceholderManager из кортежа стиля комментариев.
    
    Args:
        raw_text: исходный текст документа
        comment_style_tuple: (single_line, (multi_start, multi_end), (docstring_start, docstring_end))
        placeholder_style: Стиль плейсхолдеров
    """
    single_line, (multi_start, multi_end), (docstring_start, docstring_end) = comment_style_tuple
    
    comment_style = CommentStyle(
        single_line=single_line,
        multi_line_start=multi_start,
        multi_line_end=multi_end,
        docstring_start=docstring_start,
        docstring_end=docstring_end
    )
    
    return PlaceholderManager(raw_text, comment_style, placeholder_style)

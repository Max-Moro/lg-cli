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
    placeholder_type: str  # "function", "method", "import", "comment", "literal", etc.
    
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
    
    def can_merge_with(self, other: PlaceholderSpec) -> bool:
        """
        Проверяет, можно ли объединить этот плейсхолдер с другим.
        
        Условия объединения:
        - Одинаковый тип плейсхолдера
        - Соседние или пересекающиеся позиции (с небольшим зазором)
        """
        if self.placeholder_type != other.placeholder_type:
            return False
        
        # Проверяем близость позиций (до 2 строк разрыва)
        max_gap = 2
        if other.start_line <= self.end_line + max_gap and other.end_line >= self.start_line - max_gap:
            return True
        
        return False
    
    def merge_with(self, other: PlaceholderSpec) -> PlaceholderSpec:
        """Создает объединенный плейсхолдер."""
        if not self.can_merge_with(other):
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


class PlaceholderManager:
    """
    Центральный менеджер для управления плейсхолдерами.
    Предоставляет унифицированное API и обрабатывает коллапсирование.
    """
    
    def __init__(self, comment_style: CommentStyle, placeholder_style: str = "auto"):
        self.comment_style = comment_style
        self.placeholder_style = placeholder_style
        self.placeholders: List[PlaceholderSpec] = []
        self._pending_edits: List[Tuple[PlaceholderSpec, str]] = []  # (spec, replacement_text)
    
    # ============= Простое API для добавления плейсхолдеров =============
    
    def add_function_placeholder(self, node: Node, doc) -> None:
        """Добавить плейсхолдер для функции."""
        spec = self._create_spec_from_node(node, doc, "function")
        self._add_placeholder(spec)
    
    def add_method_placeholder(self, node: Node, doc) -> None:
        """Добавить плейсхолдер для метода."""
        spec = self._create_spec_from_node(node, doc, "method")
        self._add_placeholder(spec)
    
    def add_comment_placeholder(self, node: Node, doc, count: int = 1) -> None:
        """Добавить плейсхолдер для комментария."""
        spec = self._create_spec_from_node(node, doc, "comment", count=count)
        self._add_placeholder(spec)
    
    def add_import_placeholder(self, node: Node, doc, count: int = 1) -> None:
        """Добавить плейсхолдер для импорта."""
        spec = self._create_spec_from_node(node, doc, "import", count=count)
        self._add_placeholder(spec)
    
    def add_literal_placeholder(self, node: Node, doc, literal_type: str = "literal") -> None:
        """Добавить плейсхолдер для литерала."""
        spec = self._create_spec_from_node(node, doc, literal_type)
        self._add_placeholder(spec)
    
    def add_custom_placeholder(self, start_byte: int, end_byte: int, start_line: int, end_line: int,
                             placeholder_type: str, count: int = 1) -> None:
        """Добавить кастомный плейсхолдер с явными координатами."""
        spec = PlaceholderSpec(
            start_byte=start_byte,
            end_byte=end_byte,
            start_line=start_line,
            end_line=end_line,
            placeholder_type=placeholder_type,
            count=count,
        )
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
        
        # Определяем финальный стиль
        final_style = self._resolve_style(spec)
        
        if final_style == "inline":
            return f"{self.comment_style.single_line} {content}"
        elif final_style == "block":
            return f"{self.comment_style.multi_line_start} {content} {self.comment_style.multi_line_end}"
        else:
            # Fallback to inline
            return f"{self.comment_style.single_line} {content}"
    
    def _get_placeholder_content(self, spec: PlaceholderSpec) -> str:
        """Сгенерировать содержимое плейсхолдера на основе типа и метрик."""
        ptype = spec.placeholder_type
        count = spec.count
        lines = spec.lines_removed
        bytes_removed = spec.bytes_removed
        
        # Базовые шаблоны для разных типов
        if ptype == "function":
            if lines > 1:
                return f"… function body omitted ({lines} lines)"
            else:
                return "… function body omitted"
        
        elif ptype == "method":
            if lines > 1:
                return f"… method body omitted ({lines} lines)"
            else:
                return "… method body omitted"
        
        elif ptype == "comment":
            if count > 1:
                return f"… {count} comments omitted"
            else:
                return "… comment omitted"
        
        elif ptype == "import":
            if count > 1:
                return f"… {count} imports omitted"
            else:
                return "… import omitted"
        
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
    
    def _resolve_style(self, spec: PlaceholderSpec) -> str:
        """Определить финальный стиль плейсхолдера."""
        if self.placeholder_style in ("inline", "block"):
            return self.placeholder_style
        
        elif self.placeholder_style == "auto":
            # Автоматический выбор стиля на основе размера
            if spec.lines_removed <= 3:
                return "inline"
            else:
                return "block"
        
        else:
            # Fallback
            return "inline"
    
    # ============= Коллапсирование и финализация =============
    
    def finalize_edits(self) -> Tuple[List[Tuple[PlaceholderSpec, str]], Dict[str, Any]]:
        """
        Финализировать все правки с коллапсированием.
        
        Returns:
            (collapsed_edits, stats)
        """
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
            if current_group and current_group[-1].can_merge_with(placeholder):
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
            result = result.merge_with(placeholder)
        
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

def create_placeholder_manager(comment_style_tuple: Tuple[str, Tuple[str, str]], 
                             placeholder_style: str = "auto") -> PlaceholderManager:
    """
    Создать PlaceholderManager из кортежа стиля комментариев.
    
    Args:
        comment_style_tuple: (single_line, (multi_start, multi_end))
        placeholder_style: Стиль плейсхолдеров
    """
    single_line, (multi_start, multi_end) = comment_style_tuple
    comment_style = CommentStyle(
        single_line=single_line,
        multi_line_start=multi_start,
        multi_line_end=multi_end
    )
    
    return PlaceholderManager(comment_style, placeholder_style)

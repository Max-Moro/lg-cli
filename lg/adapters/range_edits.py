"""
Range-based text editing system for code transformations.
Provides safe text manipulation while preserving formatting and structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class TextRange:
    """Represents a range in text by byte offsets."""
    start_byte: int
    end_byte: int
    
    def __post_init__(self):
        if self.start_byte > self.end_byte:
            raise ValueError(f"Invalid range: start_byte ({self.start_byte}) > end_byte ({self.end_byte})")
    
    @property
    def length(self) -> int:
        return self.end_byte - self.start_byte
    
    def overlaps(self, other: "TextRange") -> bool:
        """Check if this range overlaps with another."""
        return not (self.end_byte <= other.start_byte or other.end_byte <= self.start_byte)
    
    def contains(self, other: "TextRange") -> bool:
        """Check if this range completely contains another."""
        return self.start_byte <= other.start_byte and other.end_byte <= self.end_byte


@dataclass
class Edit:
    """Represents a single text edit operation."""
    range: TextRange
    replacement: str
    type: Optional[str] # Тип для счетчика в метаинформации
    is_insertion: bool = False  # True если это операция вставки (range.start_byte == range.end_byte)
    
    @property
    def removes_text(self) -> bool:
        """True if this edit removes text (replacement is shorter than original)."""
        return len(self.replacement.encode('utf-8')) < self.range.length
    
    @property
    def is_deletion(self) -> bool:
        """True if this edit is a pure deletion (empty replacement)."""
        return len(self.replacement) == 0


class RangeEditor:
    """
    Safe range-based text editor that applies multiple edits while preserving structure.
    """
    
    def __init__(self, original_text: str):
        self.original_text = original_text
        self.original_bytes = original_text.encode('utf-8')
        self.edits: List[Edit] = []
    
    def add_edit(self, start_byte: int, end_byte: int, replacement: str, edit_type: Optional[str]) -> None:
        """Add an edit operation."""
        text_range = TextRange(start_byte, end_byte)

        # First-wins: если новая правка перекрывается с любой уже добавленной — тихо пропускаем её.
        for existing in self.edits:
            if text_range.overlaps(existing.range):
                return

        edit = Edit(text_range, replacement, edit_type)
        self.edits.append(edit)

    def add_deletion(self, start_byte: int, end_byte: int, edit_type: Optional[str]) -> None:
        """Add a deletion operation (empty replacement)."""
        self.add_edit(start_byte, end_byte, "", edit_type)

    def add_replacement(self, start_byte: int, end_byte: int, replacement: str, edit_type: Optional[str]) -> None:
        """Add a replacement operation."""
        self.add_edit(start_byte, end_byte, replacement, edit_type)
    
    def add_insertion(self, position_byte: int, content: str, edit_type: Optional[str]) -> None:
        """
        Add an insertion operation after the specified position.
        
        Args:
            position_byte: Byte position after which to insert content
            content: Content to insert
            edit_type: Type for statistics tracking
        """
        # Проверяем и корректируем позицию для корректной работы с UTF-8
        safe_position = self._ensure_utf8_boundary(position_byte)
        
        # Для вставки start_byte == end_byte (нулевая длина диапазона)
        text_range = TextRange(safe_position, safe_position)
        
        # Проверяем перекрытия с существующими правками
        # Для вставок перекрытие происходит если позиция вставки находится внутри существующего диапазона
        for existing in self.edits:
            if existing.is_insertion:
                # Две вставки в одной позиции - первая побеждает
                if existing.range.start_byte == safe_position:
                    return
            else:
                # Вставка перекрывается с заменой/удалением если позиция внутри диапазона
                if existing.range.start_byte < safe_position < existing.range.end_byte:
                    return
        
        edit = Edit(text_range, content, edit_type, is_insertion=True)
        self.edits.append(edit)
    
    def _ensure_utf8_boundary(self, position_byte: int) -> int:
        """
        Обеспечивает, что позиция находится на границе UTF-8 символа.
        
        Args:
            position_byte: Исходная позиция в байтах
            
        Returns:
            Безопасная позиция на границе UTF-8 символа
        """
        if position_byte <= 0 or position_byte >= len(self.original_bytes):
            return position_byte
        
        # Проверяем, находится ли позиция на границе UTF-8 символа
        try:
            # Пытаемся декодировать символ, начинающийся с этой позиции
            char_at_pos = self.original_bytes[position_byte:].decode('utf-8')[0]
            # Если успешно, позиция корректна
            return position_byte
        except UnicodeDecodeError:
            # Позиция в середине UTF-8 символа, ищем ближайшую границу
            return self._find_nearest_utf8_boundary(position_byte)
    
    def _find_nearest_utf8_boundary(self, position_byte: int) -> int:
        """
        Находит ближайшую границу UTF-8 символа.
        
        Args:
            position_byte: Позиция в середине UTF-8 символа
            
        Returns:
            Ближайшая безопасная позиция
        """
        # Сначала пытаемся найти границу, двигаясь вперед (более естественно для вставки)
        for offset in range(1, 5):
            test_pos = position_byte + offset
            if test_pos >= len(self.original_bytes):
                break
            
            try:
                # Пытаемся декодировать символ, начинающийся с этой позиции
                char = self.original_bytes[test_pos:].decode('utf-8')[0]
                # Если успешно, это граница символа
                return test_pos
            except UnicodeDecodeError:
                continue
        
        # Если не нашли границу вперед, ищем назад
        for offset in range(1, 5):  # UTF-8 символы могут быть до 4 байт
            test_pos = position_byte - offset
            if test_pos < 0:
                continue
            
            try:
                # Пытаемся декодировать символ, начинающийся с этой позиции
                char = self.original_bytes[test_pos:].decode('utf-8')[0]
                # Если успешно, это граница символа
                return test_pos
            except UnicodeDecodeError:
                continue
        
        # Fallback - возвращаем исходную позицию
        return position_byte
    
    def validate_edits(self) -> List[str]:
        """
        Validate that all edits are within bounds.
        Overlap conflicts отфильтровываются на этапе add_edit (first-wins).
        """
        errors = []

        # Check bounds only
        for i, edit in enumerate(self.edits):
            if edit.range.start_byte < 0:
                errors.append(f"Edit {i}: start_byte ({edit.range.start_byte}) is negative")
            if edit.range.end_byte > len(self.original_bytes):
                errors.append(f"Edit {i}: end_byte ({edit.range.end_byte}) exceeds text length ({len(self.original_bytes)})")

        return errors
    
    def apply_edits(self) -> Tuple[str, Dict[str, Any]]:
        """
        Apply all edits and return the modified text and statistics.
        
        Returns:
            Tuple of (modified_text, statistics)
        """
        # Validate edits first
        validation_errors = self.validate_edits()
        if validation_errors:
            raise ValueError(f"Edit validation failed: {'; '.join(validation_errors)}")
        
        if not self.edits:
            return self.original_text, {"edits_applied": 0, "bytes_removed": 0, "bytes_added": 0}
        
        # Сортируем все правки по позиции (обратный порядок для безопасного применения)
        sorted_edits = sorted(self.edits, key=lambda e: e.range.start_byte, reverse=True)
        
        result_bytes = bytearray(self.original_bytes)
        stats = {
            "edits_applied": len(self.edits),
            "bytes_removed": 0,
            "bytes_added": 0,
            "lines_removed": 0,
            "placeholders_inserted": 0,
        }
        
        # Применяем все правки от конца к началу
        for edit in sorted_edits:
            if edit.is_insertion:
                # Для вставки: вставляем контент после указанной позиции
                replacement_bytes = edit.replacement.encode('utf-8')
                stats["bytes_added"] += len(replacement_bytes)
                result_bytes[edit.range.start_byte:edit.range.start_byte] = replacement_bytes
            else:
                # Для замены/удаления: обычная логика
                original_chunk = result_bytes[edit.range.start_byte:edit.range.end_byte]
                replacement_bytes = edit.replacement.encode('utf-8')
                
                stats["bytes_removed"] += len(original_chunk)
                stats["bytes_added"] += len(replacement_bytes)
                stats["lines_removed"] += original_chunk.count(b'\n')
                
                result_bytes[edit.range.start_byte:edit.range.end_byte] = replacement_bytes
        
        # Calculate net change
        stats["bytes_saved"] = stats["bytes_removed"] - stats["bytes_added"]
        
        try:
            result_text = result_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode result text: {e}")
        
        return result_text, stats
    
    
    def get_edit_summary(self) -> Dict[str, Any]:
        """Get summary of planned edits without applying them."""
        # Для вставок range.length = 0, поэтому bytes_removed = 0
        total_bytes_removed = sum(edit.range.length for edit in self.edits if not edit.is_insertion)
        total_bytes_added = sum(len(edit.replacement.encode('utf-8')) for edit in self.edits)
        
        edit_types = {}
        for edit in self.edits:
            if edit.type:
                edit_types[edit.type] = edit_types.get(edit.type, 0) + 1
        
        return {
            "total_edits": len(self.edits),
            "bytes_to_remove": total_bytes_removed,
            "bytes_to_add": total_bytes_added,
            "net_savings": total_bytes_removed - total_bytes_added,
            "edit_types": edit_types,
        }



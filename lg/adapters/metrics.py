"""
Система сбора метрик для языковых адаптеров.
Предоставляет ленивые счетчики и безопасную работу с метаданными.
"""

from __future__ import annotations

from typing import Dict, Any, Union


class MetricsCollector:
    """
    Ленивый сборщик метрик с автоматической инициализацией счетчиков.
    Решает проблему необходимости предварительного объявления всех полей.
    """
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
    
    def increment(self, key: str, value: Union[int, float] = 1) -> None:
        """
        Ленивый инкремент - автоматически создает ключ если его нет.
        
        Args:
            key: Ключ метрики (например, "code.removed.functions")
            value: Значение для добавления (по умолчанию 1)
        """
        current = self._metrics.get(key, 0)
        if isinstance(current, (int, float)) and isinstance(value, (int, float)):
            self._metrics[key] = current + value
        else:
            # Fallback для несовместимых типов
            self._metrics[key] = value
    
    def set(self, key: str, value: Any) -> None:
        """Установить значение метрики."""
        self._metrics[key] = value
    
    def get(self, key: str, default: Any = 0) -> Any:
        """Получить значение метрики с дефолтом."""
        return self._metrics.get(key, default)
    
    def has(self, key: str) -> bool:
        """Проверить наличие метрики."""
        return key in self._metrics
    
    def add_bytes_saved(self, bytes_count: int) -> None:
        """Удобный метод для учета сэкономленных байт."""
        self.increment("code.bytes_saved", bytes_count)
    
    def add_lines_saved(self, lines_count: int) -> None:
        """Удобный метод для учета сэкономленных строк."""
        self.increment("code.lines_saved", lines_count)
    
    def mark_placeholder_inserted(self) -> None:
        """Отметить вставку плейсхолдера."""
        self.increment("code.placeholders")
    
    def mark_function_removed(self) -> None:
        """Отметить удаление функции."""
        self.increment("code.removed.functions")
    
    def mark_method_removed(self) -> None:
        """Отметить удаление метода."""
        self.increment("code.removed.methods")
    
    def mark_comment_removed(self) -> None:
        """Отметить удаление комментария."""
        self.increment("code.removed.comments")
    
    def mark_import_removed(self) -> None:
        """Отметить удаление импорта."""
        self.increment("code.removed.imports")
    
    def mark_literal_removed(self) -> None:
        """Отметить удаление литерала."""
        self.increment("code.removed.literals")
    
    def mark_field_trimmed(self) -> None:
        """Отметить обрезку поля."""
        self.increment("code.trimmed.fields")
    
    def merge(self, other: 'MetricsCollector') -> None:
        """Объединить с другим сборщиком метрик."""
        for key, value in other._metrics.items():
            if key in self._metrics and isinstance(self._metrics[key], (int, float)) and isinstance(value, (int, float)):
                self._metrics[key] = self._metrics[key] + value
            else:
                self._metrics[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Экспортировать все метрики в словарь."""
        return dict(self._metrics)
    
    def clear(self) -> None:
        """Очистить все метрики."""
        self._metrics.clear()
    
    def __repr__(self) -> str:
        return f"MetricsCollector({self._metrics})"

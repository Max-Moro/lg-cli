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
        """Метод для учета сэкономленных байт."""
        self.increment("code.bytes_saved", bytes_count)
    
    def add_lines_saved(self, lines_count: int) -> None:
        """Метод для учета сэкономленных строк."""
        self.increment("code.lines_saved", lines_count)
    
    def mark_placeholder_inserted(self) -> None:
        """Отметить вставку плейсхолдера."""
        self.increment("code.placeholders")
    
    def mark_element_removed(self, element_type: str, count: int = 1) -> None:
        """
        Универсальный метод для маркировки удаленных элементов.
        
        Args:
            element_type: Тип элемента (function, method, class, interface, etc.)
            count: Количество удаленных элементов (по умолчанию 1)
        """
        # Маппинг типов элементов в метрики во множественном числе
        element_type_to_metric = {
            "function": "functions",
            "method": "methods", 
            "class": "classes",
            "interface": "interfaces",
            "type": "types",
            "comment": "comments",
            "docstring": "docstrings",
            "import": "imports",
            "literal": "literals",
            "string": "strings",
            "array": "arrays",
            "object": "objects",
            "function_body": "function_bodies",
            "method_body": "method_bodies",
        }
        
        metric_name = element_type_to_metric.get(element_type, element_type + "s")
        metric_key = f"code.removed.{metric_name}"
        self.increment(metric_key, count)

    def merge(self, other: MetricsCollector) -> None:
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

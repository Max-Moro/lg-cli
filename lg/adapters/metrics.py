"""
Metrics collection system for language adapters.
Provides lazy counters and safe metadata handling.
"""

from __future__ import annotations

from typing import Dict, Any, Union


class MetricsCollector:
    """
    Lazy metrics collector with automatic counter initialization.
    Solves the problem of needing to pre-declare all fields.
    """
    
    def __init__(self, adapter_name: str):
        self._metrics: Dict[str, Any] = {}
        self.adapter_name: str = adapter_name

    def increment(self, key: str, value: Union[int, float] = 1) -> None:
        """
        Lazy increment - automatically creates key if it doesn't exist.

        Args:
            key: Metric key (e.g., "python.removed.function")
            value: Value to add (default 1)
        """
        current = self._metrics.get(key, 0)
        if isinstance(current, (int, float)) and isinstance(value, (int, float)):
            self._metrics[key] = current + value
        else:
            # Fallback for incompatible types
            self._metrics[key] = value
    
    def set(self, key: str, value: Any) -> None:
        """Set metric value."""
        self._metrics[key] = value

    def get(self, key: str, default: Any = 0) -> Any:
        """Get metric value with default."""
        return self._metrics.get(key, default)

    def has(self, key: str) -> bool:
        """Check if metric exists."""
        return key in self._metrics
    
    def add_chars_saved(self, chars_count: int) -> None:
        """Method to account for saved characters."""
        self.increment(self.adapter_name + ".chars_saved", chars_count)

    def add_lines_saved(self, lines_count: int) -> None:
        """Method to account for saved lines."""
        self.increment(self.adapter_name + ".lines_saved", lines_count)

    def mark_placeholder_inserted(self) -> None:
        """Mark placeholder insertion."""
        self.increment(self.adapter_name + ".placeholders")
    
    def mark_element_removed(self, element_type: str, count: int = 1) -> None:
        """
        Universal method for marking removed elements.

        Args:
            element_type: Element type (function, method, class, interface, etc.)
            count: Number of removed elements (default 1)
        """
        metric_key = f"{self.adapter_name}.removed.{element_type}"
        self.increment(metric_key, count)

    def merge(self, other: MetricsCollector) -> None:
        """Merge with another metrics collector."""
        for key, value in other._metrics.items():
            if key in self._metrics and isinstance(self._metrics[key], (int, float)) and isinstance(value, (int, float)):
                self._metrics[key] = self._metrics[key] + value
            else:
                self._metrics[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all metrics to dictionary."""
        return dict(self._metrics)

    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics.clear()
    
    def __repr__(self) -> str:
        return f"MetricsCollector({self._metrics})"

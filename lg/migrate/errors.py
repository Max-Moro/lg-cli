
from __future__ import annotations


class MigrationFatalError(RuntimeError):
    """
    Исключение верхнего уровня для фатальных сбоев миграций.
    Текст сообщения предназначен ДЛЯ ПОЛЬЗОВАТЕЛЯ (с подсказками).
    Оригинальная причина доступна через __cause__.
    """
    pass

class PreflightRequired(RuntimeError):
    """Поднимается миграцией, если для применения обязательно требуется Git."""
    pass

__all__ = ["MigrationFatalError", "PreflightRequired"]

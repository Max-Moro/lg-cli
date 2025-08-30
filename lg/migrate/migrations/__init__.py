from __future__ import annotations

# Регистрация всех доступных миграций.
from ..registry import register
from .m001_config_to_sections import MIGRATION as M001
from .m002_skip_empty_to_enum import MIGRATION as M002

register(M001)
register(M002)

__all__ = ["M001", "M002"]

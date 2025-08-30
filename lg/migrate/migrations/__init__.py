from __future__ import annotations

# Регистрация всех доступных миграций.
from ..registry import register
from .m001_config_to_sections import MIGRATION as M001

register(M001)

__all__ = ["M001"]

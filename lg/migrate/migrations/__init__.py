from __future__ import annotations

# Регистрация всех доступных миграций.
from ..registry import register_many
from .m001_config_to_sections import MIGRATION as M001
from .m002_skip_empty_to_enum import MIGRATION as M002
from .m003_contexts_flatten import MIGRATION as M003

register_many([
    M001,
    M002,
    M003
])

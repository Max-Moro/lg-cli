"""
Shared fixtures and utilities for Markdown adapter tests.
"""

# Импорт из унифицированной инфраструктуры
from tests.infrastructure.adapter_utils import make_markdown_adapter

# Для обратной совместимости
def adapter(raw_cfg: dict):
    """Markdown adapter с предустановленным TokenService."""
    return make_markdown_adapter(raw_cfg)

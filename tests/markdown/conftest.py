"""
Shared fixtures and utilities for Markdown adapter tests.
"""

# Import from unified infrastructure
from tests.infrastructure.adapter_utils import make_markdown_adapter

# For backward compatibility
def adapter(raw_cfg: dict):
    """Markdown adapter with preset TokenService."""
    return make_markdown_adapter(raw_cfg)

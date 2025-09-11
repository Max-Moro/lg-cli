"""
Shared fixtures and utilities for Markdown adapter tests.
"""

from lg.adapters.markdown import MarkdownAdapter
from lg.stats import TokenService


def adapter(raw_cfg: dict):
    """Markdown adapter с предустановленным TokenService."""
    return MarkdownAdapter().bind(raw_cfg, TokenService())

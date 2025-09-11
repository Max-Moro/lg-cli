"""
Shared fixtures and utilities for Markdown adapter tests.
"""

from lg.adapters.markdown import MarkdownAdapter
from lg.stats.tokenizer import default_tokenizer


def adapter(raw_cfg: dict):
    """Markdown adapter с предустановленным TokenService."""
    return MarkdownAdapter().bind(raw_cfg, default_tokenizer())

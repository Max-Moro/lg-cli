"""
Shared fixtures and utilities for infrastructure tests in adapters package.
Language-specific fixtures are now in their respective subpackages.
"""

import pytest

# Импорт из унифицированной инфраструктуры
from tests.infrastructure import lctx, lctx_py, lctx_ts, lctx_md  # noqa: F401

# Импорт из унифицированной инфраструктуры
from tests.infrastructure.adapter_utils import is_tree_sitter_available


@pytest.fixture
def skip_if_no_tree_sitter():
    """Skip test if Tree-sitter is not available."""
    if not is_tree_sitter_available():
        pytest.skip("Tree-sitter not available")

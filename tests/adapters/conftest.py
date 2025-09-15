"""
Shared fixtures and utilities for infrastructure tests in adapters package.
Language-specific fixtures are now in their respective subpackages.
"""

import pytest
from pathlib import Path

from tests.conftest import lctx, lctx_py, lctx_ts, lctx_md # noqa: F401


@pytest.fixture
def skip_if_no_tree_sitter():
    """Skip test if Tree-sitter is not available."""
    if not is_tree_sitter_available():
        pytest.skip("Tree-sitter not available")


def create_temp_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Create a temporary file with content."""
    file_path = tmp_path / filename
    file_path.write_text(content, encoding='utf-8')
    return file_path


def is_tree_sitter_available() -> bool:
    """Check if Tree-sitter is available for testing."""
    try:
        import tree_sitter
        import tree_sitter_python
        import tree_sitter_typescript
        return True
    except ImportError:
        return False

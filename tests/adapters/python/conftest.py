"""
Shared fixtures for Python adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample Python code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def do_comments():
    """Sample Python code for testing comment optimization."""
    return load_sample_code("comments")


@pytest.fixture
def do_literals():
    """Sample Python code for testing literal optimization."""
    return load_sample_code("literals")


@pytest.fixture
def do_imports():
    """Sample Python code for testing import optimization."""
    return load_sample_code("imports")


@pytest.fixture
def do_public_api():
    """Sample Python code for testing public API filtering."""
    return load_sample_code("public_api")


@pytest.fixture
def do_fields():
    """Sample Python code for testing field optimization."""
    return load_sample_code("fields")


@pytest.fixture
def do_complex():
    """Sample Python code for testing complex combined optimization."""
    return load_sample_code("complex")


@pytest.fixture
def do_trivial():
    """__init__.py with docstring and __all__ only."""
    return load_sample_code("trivial_init")


@pytest.fixture
def do_non_trivial():
    """__init__.py with convenience function."""
    return load_sample_code("non_trivial_init")


@pytest.fixture
def do_trivial_annotated():
    """__init__.py with annotated __all__ declaration."""
    return load_sample_code("trivial_init_annotated")

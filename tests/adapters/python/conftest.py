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
def do_trivial_init_empty():
    """Empty __init__.py file with only docstring."""
    return load_sample_code("trivial_init_empty")


@pytest.fixture
def do_trivial_init_reexports():
    """__init__.py with only re-exports."""
    return load_sample_code("trivial_init_reexports")


@pytest.fixture
def do_trivial_init_docstring_and_all():
    """__init__.py with docstring and __all__ only."""
    return load_sample_code("trivial_init_docstring_and_all")


@pytest.fixture
def do_non_trivial_init():
    """__init__.py with convenience function - realistic non-trivial example."""
    return load_sample_code("non_trivial_init_function")

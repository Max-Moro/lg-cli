"""
Shared fixtures for TypeScript adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample TypeScript code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def do_comments():
    """Sample TypeScript code for testing comment optimization."""
    return load_sample_code("comments")


@pytest.fixture
def do_literals():
    """Sample TypeScript code for testing literal optimization."""
    return load_sample_code("literals")


@pytest.fixture
def do_imports():
    """Sample TypeScript code for testing import optimization."""
    return load_sample_code("imports")


@pytest.fixture
def do_public_api():
    """Sample TypeScript code for testing public API filtering."""
    return load_sample_code("public_api")


@pytest.fixture
def do_fields():
    """Sample TypeScript code for testing field optimization."""
    return load_sample_code("fields")


@pytest.fixture
def do_complex():
    """Sample TypeScript code for testing complex combined optimization."""
    return load_sample_code("complex")


@pytest.fixture
def do_trivial_barrel():
    """Barrel file with only re-exports."""
    return load_sample_code("trivial_barrel")


@pytest.fixture
def do_trivial_barrel_with_comments():
    """Barrel file with comments and re-exports."""
    return load_sample_code("trivial_barrel_with_comments")


@pytest.fixture
def do_trivial_barrel_type_only():
    """Barrel file with only type exports."""
    return load_sample_code("trivial_barrel_type_only")


@pytest.fixture
def do_non_trivial_barrel():
    """Barrel file with convenience function - realistic non-trivial example."""
    return load_sample_code("non_trivial_barrel_function")

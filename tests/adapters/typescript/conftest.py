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
def barrel_file_sample():
    """Sample TypeScript barrel file for testing."""
    return load_sample_code("barrel_file_sample")


@pytest.fixture
def non_barrel_file_sample():
    """Sample TypeScript non-barrel file for testing."""
    return load_sample_code("non_barrel_file_sample")


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

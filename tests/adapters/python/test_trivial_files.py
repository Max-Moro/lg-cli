"""
Tests for trivial file detection in Python adapter.

These tests use TDD approach - they are written before the implementation.
The tests should fail until PythonTrivialAnalyzer is implemented.
"""

from pathlib import Path

import pytest

from lg.adapters.langs.python import PythonCfg
from .utils import lctx, make_adapter


class TestPythonTrivialInitFiles:
    """Test trivial __init__.py detection."""

    # ============= Trivial cases (should be skipped) =============

    def test_empty_init_is_trivial(self, do_trivial_init_empty):
        """Empty __init__.py with only docstring should be skipped."""
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_empty, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_reexports_only_is_trivial(self, do_trivial_init_reexports):
        """__init__.py with only re-exports should be skipped."""
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_reexports, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_docstring_and_all_is_trivial(self, do_trivial_init_docstring_and_all):
        """__init__.py with docstring and __all__ only should be skipped."""
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_docstring_and_all, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True

    # ============= Non-trivial cases (should NOT be skipped) =============

    def test_with_convenience_function_is_not_trivial(self, do_non_trivial_init):
        """__init__.py with convenience function should NOT be skipped.

        Real packages often add helper functions for user convenience.
        These should be visible to AI agents.
        """
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_non_trivial_init, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is False

    # ============= Filename checks =============

    def test_non_init_file_never_trivial(self, do_trivial_init_reexports):
        """Non-__init__.py files should never be considered trivial."""
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        # Same trivial content but different filename
        ctx = lctx(do_trivial_init_reexports, Path("/pkg/utils.py"))
        assert analyzer.is_trivial(ctx, adapter) is False

    def test_init_in_nested_package(self, do_trivial_init_reexports):
        """__init__.py in nested package should be detected."""
        from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer

        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_reexports, Path("/pkg/subpkg/deep/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True


class TestPythonTrivialFilesIntegration:
    """Test integration with adapter's should_skip method."""

    def test_adapter_should_skip_trivial_init(self, do_trivial_init_reexports):
        """Adapter should skip trivial __init__.py via should_skip()."""
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_reexports, Path("/pkg/__init__.py"))
        assert adapter.should_skip(ctx) is True

    def test_adapter_should_not_skip_non_trivial_init(self, do_non_trivial_init):
        """Adapter should NOT skip non-trivial __init__.py."""
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_non_trivial_init, Path("/pkg/__init__.py"))
        assert adapter.should_skip(ctx) is False

    def test_adapter_should_not_skip_regular_file(self, do_trivial_init_reexports):
        """Adapter should NOT skip regular Python files."""
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_reexports, Path("/pkg/module.py"))
        assert adapter.should_skip(ctx) is False

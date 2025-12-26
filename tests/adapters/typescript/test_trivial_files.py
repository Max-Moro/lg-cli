"""
Tests for trivial file detection in TypeScript adapter.

These tests use TDD approach - they are written before the implementation.
The tests should fail until TypeScriptTrivialAnalyzer is implemented.
"""

from pathlib import Path

import pytest

from lg.adapters.langs.typescript import TypeScriptCfg
from .utils import lctx, make_adapter


class TestTypeScriptTrivialBarrelFiles:
    """Test trivial barrel file (index.ts) detection."""

    # ============= Trivial cases (should be skipped) =============

    def test_reexports_only_is_trivial(self, do_trivial_barrel):
        """index.ts with only re-exports should be skipped."""
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_reexports_with_comments_is_trivial(self, do_trivial_barrel_with_comments):
        """index.ts with comments and re-exports should be skipped."""
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel_with_comments, Path("/src/components/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_type_only_exports_is_trivial(self, do_trivial_barrel_type_only):
        """index.ts with only type exports should be skipped."""
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel_type_only, Path("/src/types/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is True

    # ============= Non-trivial cases (should NOT be skipped) =============

    def test_with_convenience_function_is_not_trivial(self, do_non_trivial_barrel):
        """index.ts with convenience function should NOT be skipped.

        Real barrel files sometimes include helper functions.
        These should be visible to AI agents.
        """
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_non_trivial_barrel, Path("/src/components/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is False

    # ============= Filename checks =============

    def test_non_index_file_never_trivial(self, do_trivial_barrel):
        """Non-index.ts files should never be considered trivial."""
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        # Same trivial content but different filename
        ctx = lctx(do_trivial_barrel, Path("/src/components/exports.ts"))
        assert analyzer.is_trivial(ctx, adapter) is False

    def test_index_tsx_is_checked(self, do_trivial_barrel):
        """index.tsx should also be checked for triviality."""
        from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer

        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/index.tsx"))
        assert analyzer.is_trivial(ctx, adapter) is True


class TestTypeScriptTrivialFilesIntegration:
    """Test integration with adapter's should_skip method."""

    def test_adapter_should_skip_trivial_barrel(self, do_trivial_barrel):
        """Adapter should skip trivial index.ts via should_skip()."""
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/index.ts"))
        assert adapter.should_skip(ctx) is True

    def test_adapter_should_not_skip_non_trivial_barrel(self, do_non_trivial_barrel):
        """Adapter should NOT skip non-trivial index.ts."""
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_non_trivial_barrel, Path("/src/components/index.ts"))
        assert adapter.should_skip(ctx) is False

    def test_adapter_should_not_skip_regular_file(self, do_trivial_barrel):
        """Adapter should NOT skip regular TypeScript files."""
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/Button.ts"))
        assert adapter.should_skip(ctx) is False

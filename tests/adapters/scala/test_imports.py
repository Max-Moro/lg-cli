"""
Tests for import optimization in Scala adapter.
"""

from lg.adapters.scala import ScalaCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestScalaImportOptimization:
    """Test Scala import optimization policies."""

    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(ScalaCfg())

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("scala.removed.imports", 0) == 0
        assert "import scala.collection.mutable" in result
        assert "import scala.concurrent._" in result

        assert_golden_match(result, "imports", "keep_all")

    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(ScalaCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("scala.removed.import", 0) > 0

        assert "import scala.collection.mutable" in result
        assert "import scala.concurrent._" in result

        assert "com.example.imports.services" not in result
        assert "// … imports omitted" in result

        assert_golden_match(result, "imports", "strip_local")

    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(ScalaCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("scala.removed.import", 0) > 0

        assert "com.example.imports.services" in result

        assert "// …" in result and "omitted" in result

        assert_golden_match(result, "imports", "strip_external")

    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(ScalaCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("scala.removed.import", 0) > 0

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith('import')]
        assert len(import_lines) < 10

        assert_golden_match(result, "imports", "strip_all")

    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5
        )

        adapter = make_adapter(ScalaCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("scala.removed.import", 0) > 0
        assert "// … " in result and "imports omitted" in result

        assert_golden_match(result, "imports", "summarize_long")

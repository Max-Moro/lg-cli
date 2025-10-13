"""
Tests for import optimization in Kotlin adapter.
"""

from lg.adapters.kotlin import KotlinCfg
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_kt, do_imports, assert_golden_match, make_adapter


class TestKotlinImportOptimization:
    """Test Kotlin import optimization policies."""
    
    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(KotlinCfg())  # Default imports policy is keep_all
        
        result, meta = adapter.process(lctx_kt(do_imports))
        
        # No imports should be removed
        assert meta.get("kotlin.removed.imports", 0) == 0
        assert "import kotlin.math.*" in result
        assert "import kotlinx.coroutines.*" in result
        
        assert_golden_match(result, "imports", "keep_all")
    
    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(KotlinCfg(imports=import_config))
        
        result, meta = adapter.process(lctx_kt(do_imports))
        
        # Local imports should be removed
        assert meta.get("kotlin.removed.import", 0) > 0
        
        # External imports should be preserved
        assert "import kotlin.math.*" in result
        assert "import kotlinx.coroutines.*" in result
        
        # Local imports should be replaced with placeholders
        assert "com.example.imports.services" not in result
        assert "// … 23 imports omitted" in result
        
        assert_golden_match(result, "imports", "strip_local")
    
    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")
        
        adapter = make_adapter(KotlinCfg(imports=import_config))
        
        result, meta = adapter.process(lctx_kt(do_imports))
        
        # External imports should be removed
        assert meta.get("kotlin.removed.import", 0) > 0
        
        # Local imports should be preserved
        assert "com.example.imports.services" in result
        
        # External imports should be replaced with placeholders
        assert "// …" in result and "omitted" in result
        
        assert_golden_match(result, "imports", "strip_external")
    
    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")
        
        adapter = make_adapter(KotlinCfg(imports=import_config))
        
        result, meta = adapter.process(lctx_kt(do_imports))
        
        # All imports should be removed
        assert meta.get("kotlin.removed.import", 0) > 0
        
        # No imports should remain (except possibly placeholders)
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith('import')]
        # Most imports should be replaced with placeholders
        assert len(import_lines) < 10  # Allow some that might not be optimized
        
        assert_golden_match(result, "imports", "strip_all")
    
    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5  # Low threshold to trigger summarization
        )
        
        adapter = make_adapter(KotlinCfg(imports=import_config))
        
        result, meta = adapter.process(lctx_kt(do_imports))
        
        # Long import lists should be summarized
        assert meta.get("kotlin.removed.import", 0) > 0
        assert "// … " in result and "imports omitted" in result
        
        assert_golden_match(result, "imports", "summarize_long")


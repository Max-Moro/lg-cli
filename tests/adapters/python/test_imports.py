"""
Tests for import optimization in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.python.imports import PythonImportClassifier, PythonImportAnalyzer
from lg.adapters.python.adapter import PythonDocument
from lg.adapters.code_model import ImportConfig
from .conftest import create_python_context


class TestPythonImportClassifier:
    """Test import classification logic for Python."""
    
    def test_external_classification(self):
        """Test classification of Python external packages."""
        classifier = PythonImportClassifier()
        
        # Common external packages should be detected
        assert classifier.is_external("numpy") is True
        assert classifier.is_external("pandas") is True
        assert classifier.is_external("requests") is True
        assert classifier.is_external("os") is True  # Standard library
        assert classifier.is_external("sys") is True
        
        # Local imports should be detected
        assert classifier.is_external(".module") is False  # Relative
        assert classifier.is_external("..parent") is False  # Relative
        assert classifier.is_external("src.utils") is False  # Local pattern
        assert classifier.is_external("MyModule") is False  # PascalCase
        assert classifier.is_external("app.models.user") is False  # Deep local
    
    def test_custom_patterns(self):
        """Test custom external patterns."""
        patterns = [r"^myorg-.*", r"^@mycompany/.*"]
        classifier = PythonImportClassifier(patterns)
        
        assert classifier.is_external("myorg-utils") is True
        assert classifier.is_external("@mycompany/shared") is True
        assert classifier.is_external("regular-package") is True  # Still detected by defaults
        assert classifier.is_external("./local") is False


class TestPythonImportAnalyzer:
    """Test import analysis functionality for Python."""
    
    def test_import_parsing(self):
        """Test parsing Python import statements."""

        code = '''import os
import sys, json
import numpy as np
from pathlib import Path
from myapp.utils import helper
from .relative import something
'''
        
        doc = PythonDocument(code, "py")
        classifier = PythonImportClassifier()
        analyzer = PythonImportAnalyzer(classifier)
        imports = analyzer.analyze_imports(doc)
        
        # Should find all imports
        assert len(imports) >= 4  # At least the main import statements
        
        # Check specific imports
        import_modules = [imp.module_name for imp in imports]
        assert "os" in import_modules
        assert "pathlib" in import_modules or "Path" in str(imports)  # Could be parsed differently
        assert "myapp.utils" in import_modules
    
    def test_import_grouping(self):
        """Test grouping imports by external vs local."""

        code = '''import numpy as np
import pandas as pd
from myapp.models import User
from .utils import helper
'''
        
        doc = PythonDocument(code, "python")
        classifier = PythonImportClassifier()
        analyzer = PythonImportAnalyzer(classifier)
        imports = analyzer.analyze_imports(doc)
        grouped = analyzer.group_imports(imports)
        
        assert "external" in grouped
        assert "local" in grouped
        assert len(grouped["external"]) >= 2  # numpy, pandas
        assert len(grouped["local"]) >= 2    # myapp.*, .utils


class TestPythonImportOptimization:
    """Test import optimization for Python code."""
    
    def test_keep_all_policy(self):
        """Test that keep_all preserves all imports."""
        code = '''import os
import sys
import numpy as np
from myapp.utils import helper
from .relative import something

def main():
    pass
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(policy="keep_all")
        adapter._cfg = PythonCfg(imports=import_config)
        
        result, meta = adapter.process(create_python_context(code))
        
        # All imports should be preserved
        assert "import os" in result
        assert "import sys" in result
        assert "import numpy as np" in result
        assert "from myapp.utils import helper" in result
        assert "from .relative import something" in result
        assert meta.get("code.removed.imports", 0) == 0
    
    def test_external_only_policy(self):
        """Test that external_only removes local imports."""
        code = '''import os
import sys
import numpy as np
from myapp.utils import helper
from .relative import something

def main():
    pass
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(imports=import_config)
        
        result, meta = adapter.process(create_python_context(code))
        
        # External imports should be preserved
        assert "import os" in result
        assert "import sys" in result
        assert "import numpy as np" in result
        
        # Local imports should be removed/replaced with placeholders
        assert "# … 1 imports omitted" in result or "from myapp.utils import helper" not in result
        assert meta["code.removed.imports"] > 0
    
    def test_summarize_long_policy(self):
        """Test that summarize_long condenses many imports."""
        # Create code with many imports
        imports = []
        for i in range(15):  # More than default max_items_before_summary (10)
            imports.append(f"import module{i}")
        
        code = '\n'.join(imports) + '''

def main():
    pass
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(
            policy="summarize_long",
            max_items_before_summary=5  # Lower threshold for testing
        )
        adapter._cfg = PythonCfg(imports=import_config)
        
        result, meta = adapter.process(create_python_context(code))
        
        # Should contain summarization placeholders
        assert "external imports" in result or meta["code.removed.imports"] > 0
        # Should be shorter than original
        assert len(result) < len(code)


class TestPythonImportEdgeCases:
    """Test edge cases for Python import optimization."""
    
    def test_no_imports(self):
        """Test processing file without imports."""
        code = '''def main():
    print("Hello world")
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(imports=import_config)
        
        result, meta = adapter.process(create_python_context(code))
        
        assert result == code  # Should be unchanged
        assert meta.get("code.removed.imports", 0) == 0
    
    def test_mixed_import_types(self):
        """Test processing mixed import types."""
        code = '''import os  # Standard library
import numpy  # External package
from myapp import utils  # Local package
from .relative import helper  # Relative import

def main():
    pass
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(
            policy="external_only",
            external_only_patterns=["^myapp.*"]  # Treat myapp as external
        )
        adapter._cfg = PythonCfg(imports=import_config)
        
        result, meta = adapter.process(create_python_context(code))
        
        # Should preserve os, numpy, and myapp (due to custom pattern)
        assert "import os" in result
        assert "import numpy" in result
        assert "from myapp import utils" in result
        
        # Should remove relative import
        assert meta["code.removed.imports"] > 0
    
    def test_placeholder_styles(self):
        """Test different placeholder styles for imports."""
        code = '''from .local import something

def main():
    pass
'''
        
        adapter = PythonAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(imports=import_config)
        
        # Test inline style
        adapter._cfg.placeholders.style = "inline"
        result, meta = adapter.process(create_python_context(code))
        assert "# … 1 imports omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(create_python_context(code))
        # For Python, block style might still use # comments
        assert "imports omitted" in result  # Should still contain the message

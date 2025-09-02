"""
Tests for import optimization implementation (M3).
"""

import pytest

from lg.adapters.code_model import ImportConfig
from lg.adapters.import_utils import ImportClassifier, ImportAnalyzer
from lg.adapters.python_tree_sitter import PythonTreeSitterAdapter, PythonCfg
from lg.adapters.typescript_tree_sitter import TypeScriptTreeSitterAdapter, TypeScriptCfg

pytestmark = pytest.mark.usefixtures("skip_if_no_tree_sitter")


class TestImportClassifier:
    """Test import classification logic."""
    
    def test_python_external_classification(self):
        """Test classification of Python external packages."""
        classifier = ImportClassifier()
        
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
    
    def test_typescript_external_classification(self):
        """Test classification of TypeScript/JavaScript external packages."""
        classifier = ImportClassifier()
        
        # External packages
        assert classifier.is_external("react") is True
        assert classifier.is_external("@angular/core") is True
        assert classifier.is_external("lodash") is True
        assert classifier.is_external("express") is True
        
        # Local imports
        assert classifier.is_external("./component") is False
        assert classifier.is_external("../utils") is False
        assert classifier.is_external("src/services") is False
        assert classifier.is_external("components/Button") is False
    
    def test_custom_patterns(self):
        """Test custom external patterns."""
        patterns = [r"^myorg-.*", r"^@mycompany/.*"]
        classifier = ImportClassifier(patterns)
        
        assert classifier.is_external("myorg-utils") is True
        assert classifier.is_external("@mycompany/shared") is True
        assert classifier.is_external("regular-package") is True  # Still detected by defaults
        assert classifier.is_external("./local") is False


class TestImportAnalyzer:
    """Test import analysis functionality."""
    
    def test_python_import_parsing(self):
        """Test parsing Python import statements."""
        from lg.adapters.tree_sitter_support import create_document
        
        code = '''import os
import sys, json
import numpy as np
from pathlib import Path
from myapp.utils import helper
from .relative import something
'''
        
        doc = create_document(code, "python")
        analyzer = ImportAnalyzer()
        imports = analyzer.analyze_imports(doc)
        
        # Should find all imports
        assert len(imports) >= 4  # At least the main import statements
        
        # Check specific imports
        import_modules = [imp.module_name for imp in imports]
        assert "os" in import_modules
        assert "pathlib" in import_modules or "Path" in str(imports)  # Could be parsed differently
        assert "myapp.utils" in import_modules
    
    def test_typescript_import_parsing(self):
        """Test parsing TypeScript import statements."""
        from lg.adapters.tree_sitter_support import create_document
        
        code = '''import React from 'react';
import { Component, OnInit } from '@angular/core';
import * as fs from 'fs';
import './styles.css';
import { helper } from '../utils/helper';
'''
        
        doc = create_document(code, "typescript")
        analyzer = ImportAnalyzer()
        imports = analyzer.analyze_imports(doc)
        
        # Should find all imports
        assert len(imports) >= 4
        
        # Check specific imports
        import_modules = [imp.module_name for imp in imports]
        assert "react" in import_modules
        assert "@angular/core" in import_modules
        assert "fs" in import_modules
    
    def test_import_grouping(self):
        """Test grouping imports by external vs local."""
        from lg.adapters.tree_sitter_support import create_document
        
        code = '''import numpy as np
import pandas as pd
from myapp.models import User
from .utils import helper
'''
        
        doc = create_document(code, "python")
        analyzer = ImportAnalyzer()
        imports = analyzer.analyze_imports(doc)
        grouped = analyzer.group_imports(imports)
        
        assert "external" in grouped
        assert "local" in grouped
        assert len(grouped["external"]) >= 2  # numpy, pandas
        assert len(grouped["local"]) >= 2    # myapp.*, .utils


class TestImportOptimizationPython:
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
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(policy="keep_all")
        adapter._cfg = PythonCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # All imports should be preserved
        assert "import os" in result
        assert "import sys" in result
        assert "import numpy as np" in result
        assert "from myapp.utils import helper" in result
        assert "from .relative import something" in result
        assert meta["code.removed.imports"] == 0
    
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
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
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
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(
            policy="summarize_long",
            max_items_before_summary=5  # Lower threshold for testing
        )
        adapter._cfg = PythonCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should contain summarization placeholders
        assert "external imports" in result or meta["code.removed.imports"] > 0
        # Should be shorter than original
        assert len(result) < len(code)


class TestImportOptimizationTypeScript:
    """Test import optimization for TypeScript code."""
    
    def test_external_only_policy(self):
        """Test external_only policy for TypeScript."""
        code = '''import React from 'react';
import { Component } from '@angular/core';
import { helper } from './utils/helper';
import '../styles.css';

export class MyComponent {
}
'''
        
        adapter = TypeScriptTreeSitterAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = TypeScriptCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # External imports should be preserved
        assert "react" in result
        assert "@angular/core" in result
        
        # Local imports should be processed
        assert meta["code.removed.imports"] > 0 or "// … 1 imports omitted" in result
    
    def test_summarize_long_imports(self):
        """Test summarization of many TypeScript imports."""
        imports = []
        for i in range(12):
            imports.append(f"import module{i} from 'package{i}';")
        
        code = '\n'.join(imports) + '''

export class MyClass {
}
'''
        
        adapter = TypeScriptTreeSitterAdapter()
        import_config = ImportConfig(
            policy="summarize_long",
            max_items_before_summary=5
        )
        adapter._cfg = TypeScriptCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should be summarized
        assert "external imports" in result or meta["code.removed.imports"] > 0


class TestImportOptimizationEdgeCases:
    """Test edge cases for import optimization."""
    
    def test_no_imports(self):
        """Test processing file without imports."""
        code = '''def main():
    print("Hello world")
'''
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        assert result == code  # Should be unchanged
        assert meta["code.removed.imports"] == 0
    
    def test_mixed_import_types(self):
        """Test processing mixed import types."""
        code = '''import os  # Standard library
import numpy  # External package
from myapp import utils  # Local package
from .relative import helper  # Relative import

def main():
    pass
'''
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(
            policy="external_only",
            external_only_patterns=["^myapp.*"]  # Treat myapp as external
        )
        adapter._cfg = PythonCfg(import_config=import_config)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
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
        
        adapter = PythonTreeSitterAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = PythonCfg(import_config=import_config)
        
        # Test inline style
        adapter._cfg.placeholders.style = "inline"
        result, meta = adapter.process(code, group_size=1, mixed=False)
        assert "# … 1 imports omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(code, group_size=1, mixed=False)
        assert "imports omitted" in result  # Should still contain the message

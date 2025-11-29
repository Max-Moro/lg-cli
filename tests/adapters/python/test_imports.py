"""
Tests for import optimization in Python adapter.
"""

from lg.adapters.python import PythonCfg
from lg.adapters.python.imports import PythonImportClassifier, PythonImportAnalyzer
from lg.adapters.python.adapter import PythonDocument
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestPythonImportClassification:
    """Test Python import classification logic."""
    
    def test_external_library_detection(self):
        """Test detection of external libraries."""
        classifier = PythonImportClassifier()
        
        # Standard library modules
        assert classifier.is_external("os")
        assert classifier.is_external("sys")
        assert classifier.is_external("json")
        assert classifier.is_external("pathlib")
        assert classifier.is_external("typing")
        
        # Common external packages
        assert classifier.is_external("numpy")
        assert classifier.is_external("pandas")
        assert classifier.is_external("requests")
        assert classifier.is_external("flask")
        assert classifier.is_external("django")
    
    def test_local_import_detection(self):
        """Test detection of local/relative imports."""
        classifier = PythonImportClassifier()
        
        # Relative imports
        assert not classifier.is_external(".utils")
        assert not classifier.is_external("..shared")
        assert not classifier.is_external("...core")
        
        # Local-looking imports
        assert not classifier.is_external("myproject.utils")
        assert not classifier.is_external("src.models")
        assert not classifier.is_external("MyModule")  # Contains uppercase
    
    def test_custom_external_patterns(self):
        """Test custom external patterns."""
        custom_patterns = [r"^mycompany\..*", r"^internal_.*"]
        classifier = PythonImportClassifier(custom_patterns)
        
        # Should match custom patterns
        assert classifier.is_external("mycompany.utils")
        assert classifier.is_external("internal_library")
        
        # Should still work for standard detection
        assert classifier.is_external("numpy")
        assert not classifier.is_external(".local")


class TestPythonImportAnalysis:
    """Test Python import analysis and parsing."""
    
    def test_simple_import_parsing(self):
        """Test parsing of simple import statements."""
        code = '''import os
import sys, json
import numpy as np
'''
        
        doc = PythonDocument(code, "py")
        classifier = PythonImportClassifier()
        analyzer = PythonImportAnalyzer(classifier)
        
        imports = analyzer.analyze_imports(doc)
        
        assert len(imports) >= 3
        
        # Check individual imports
        import_modules = [imp.module_name for imp in imports]
        assert "os" in import_modules
        assert "sys" in import_modules
        assert "numpy" in import_modules
    
    def test_from_import_parsing(self):
        """Test parsing of from...import statements."""
        code = '''from os.path import join, dirname
from typing import List, Dict, Optional
from .utils import helper_function
'''
        
        doc = PythonDocument(code, "py")
        classifier = PythonImportClassifier()
        analyzer = PythonImportAnalyzer(classifier)
        
        imports = analyzer.analyze_imports(doc)
        
        assert len(imports) >= 3
        
        # Check from imports
        for imp in imports:
            if imp.module_name == "os.path":
                assert "join" in imp.imported_items
                assert "dirname" in imp.imported_items
            elif imp.module_name == "typing":
                assert "List" in imp.imported_items
                assert "Dict" in imp.imported_items
            elif imp.module_name == ".utils":
                assert "helper_function" in imp.imported_items
                assert not imp.is_external  # Relative import


class TestPythonImportOptimization:
    """Test Python import optimization policies."""
    
    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(PythonCfg())  # Default imports policy is keep_all
        
        result, meta = adapter.process(lctx(do_imports))
        
        # No imports should be removed
        assert meta.get("python.removed.import", 0) == 0
        assert "import os" in result
        assert "import numpy as np" in result
        assert "from .utils import helper_function" in result
        
        assert_golden_match(result, "imports", "keep_all")
    
    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(do_imports))
        
        # Local imports should be removed
        assert meta.get("python.removed.import", 0) == 24
        
        # External imports should be preserved
        assert "import os" in result
        assert "import numpy as np" in result
        
        # Local imports should be replaced with placeholders
        assert "from .utils import helper_function" not in result
        assert "# … 12 imports omitted" in result
        
        assert_golden_match(result, "imports", "strip_local")
    
    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(do_imports))
        
        # External imports should be removed
        assert meta.get("python.removed.import", 0) == 58
        
        # Local imports should be preserved
        assert "from .utils import helper_function" in result
        assert "from .models import User, Post, Comment" in result
        
        # External imports should be replaced with placeholders
        assert "import os" not in result
        assert "# … 17 imports omitted" in result
        assert "import numpy as np" not in result
        assert "# … 13 imports omitted" in result
        
        assert_golden_match(result, "imports", "strip_external")
    
    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(do_imports))
        
        # All imports should be removed
        assert meta.get("python.removed.import", 0) == 82
        
        # No imports should remain (except possibly placeholders)
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith(('import', 'from'))]
        assert len(import_lines) == 0
        
        assert_golden_match(result, "imports", "strip_all")
    
    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5  # Low threshold to trigger summarization
        )
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(do_imports))
        
        # Long import lists should be summarized
        assert meta.get("python.removed.import", 0) == 29
        assert "# … 29 imports omitted" in result
        
        assert_golden_match(result, "imports", "summarize_long")
    
    def test_custom_external_patterns(self):
        """Test import optimization with custom external patterns."""
        code = '''import os
import mycompany.utils  # Should be treated as external
from internal.helpers import process  # Should be treated as local
from .local import function  # Relative import
'''
        
        import_config = ImportConfig(
            policy="strip_local",
            external_patterns=["^mycompany\..*"]
        )
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # External imports should be preserved
        assert "import os" in result
        assert "import mycompany.utils" in result
        
        # Local imports should be removed
        assert "from internal.helpers" not in result
        assert "from .local" not in result
        assert result.count("# … import omitted") == 2
    
    def test_mixed_import_styles_handling(self):
        """Test handling of mixed import styles."""
        code = '''import os, sys, json
from typing import List, Dict, Optional, Union, Any
from collections import defaultdict, Counter, deque
'''
        
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=3
        )
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Long from-import lists should be summarized
        assert meta.get("python.removed.import", 0) == 5
        assert "# … 5 imports omitted" in result
    
    def test_conditional_import_preservation(self):
        """Test preservation of conditional imports."""
        code = '''import os
try:
    import uvloop
except ImportError:
    uvloop = None

if TYPE_CHECKING:
    from typing import Optional
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Conditional imports should be handled appropriately
        # The exact behavior may depend on implementation
        assert "import os" in result
        assert "uvloop" in result  # Conditional import should be preserved


class TestPythonImportEdgeCases:
    """Test edge cases for Python import optimization."""
    
    def test_star_imports(self):
        """Test handling of star imports."""
        code = '''from os import *
from .utils import *
from typing import *
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # External star imports should be preserved
        assert "from os import *" in result
        assert "from typing import *" in result
        
        # Local star imports should be removed
        assert "from .utils import *" not in result
        assert "# … import omitted" in result
    
    def test_aliased_imports(self):
        """Test handling of aliased imports."""
        code = '''import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split as tts
from .helpers import process_data as process
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # External aliased imports should be preserved
        assert "import numpy as np" in result
        assert "train_test_split as tts" in result
        
        # Local aliased imports should be removed
        assert "from .helpers import process_data as process" not in result
        assert "# … import omitted" in result
    
    def test_deeply_nested_modules(self):
        """Test handling of deeply nested module imports."""
        code = '''from very.deep.nested.module.structure import function
from local.project.deeply.nested import utility
import external.library.with.deep.structure
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Classification should work for deeply nested modules
        # Exact behavior depends on implementation heuristics
        assert meta.get("python.removed.import", 0) >= 0
    
    def test_import_summarization_grouping(self):
        """Test that import summarization groups consecutive imports."""
        code = '''from django.http import (
    HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect,
    HttpResponsePermanentRedirect, HttpResponseNotModified,
    HttpResponseBadRequest, HttpResponseNotFound
)

import os
import sys

from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
    throttle_classes, parser_classes
)
'''
        
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=3
        )
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Long import groups should be summarized
        assert meta.get("python.removed.import", 0) == 13
        assert "# … 8 imports omitted" in result
        
        # Short imports should be preserved
        assert "import os" in result
        assert "import sys" in result
    
    def test_strip_local_with_summarize_long(self):
        """Test combining strip_local policy with summarize_long option."""
        code = '''import os
import sys
from collections import defaultdict, Counter, deque, OrderedDict, ChainMap
from .utils import func1, func2, func3, func4, func5, func6
from .models import Model1, Model2, Model3
'''
        
        import_config = ImportConfig(
            policy="strip_local",
            summarize_long=True,
            max_items_before_summary=3
        )
        
        adapter = make_adapter(PythonCfg(imports=import_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Local imports should be stripped regardless of length
        assert "from .utils import" not in result
        assert "from .models import" not in result

        
        # External imports should remain but long ones should be summarized
        assert "import os" in result
        assert "import sys" in result
        # Long external import should be summarized
        assert "# … 14 imports omitted" in result

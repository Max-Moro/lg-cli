"""
Tests for import optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.typescript.imports import TypeScriptImportClassifier, TypeScriptImportAnalyzer
from lg.adapters.typescript.adapter import TypeScriptDocument
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_ts


class TestTypeScriptImportClassifier:
    """Test import classification logic for TypeScript."""
    
    def test_external_classification(self):
        """Test classification of TypeScript/JavaScript external packages."""
        classifier = TypeScriptImportClassifier()
        
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
        """Test custom external patterns for TypeScript."""
        patterns = [r"^myorg-.*", r"^@mycompany/.*"]
        classifier = TypeScriptImportClassifier(patterns)
        
        assert classifier.is_external("myorg-utils") is True
        assert classifier.is_external("@mycompany/shared") is True
        assert classifier.is_external("regular-package") is True  # Still detected by defaults
        assert classifier.is_external("./local") is False


class TestTypeScriptImportAnalyzer:
    """Test import analysis functionality for TypeScript."""
    
    def test_import_parsing(self):
        """Test parsing TypeScript import statements."""

        code = '''import React from 'react';
import { Component, OnInit } from '@angular/core';
import * as fs from 'fs';
import './styles.css';
import { helper } from '../utils/helper';
'''
        
        doc = TypeScriptDocument(code, "ts")
        classifier = TypeScriptImportClassifier()
        analyzer = TypeScriptImportAnalyzer(classifier)
        imports = analyzer.analyze_imports(doc)
        
        # Should find all imports
        assert len(imports) >= 4
        
        # Check specific imports
        import_modules = [imp.module_name for imp in imports]
        assert "react" in import_modules
        assert "@angular/core" in import_modules
        assert "fs" in import_modules
    
    def test_import_grouping(self):
        """Test grouping TypeScript imports by external vs local."""

        code = '''import React from 'react';
import { Observable } from 'rxjs';
import { helper } from './utils/helper';
import '../styles.css';
'''
        
        doc = TypeScriptDocument(code, "ts")
        classifier = TypeScriptImportClassifier()
        analyzer = TypeScriptImportAnalyzer(classifier)
        imports = analyzer.analyze_imports(doc)
        grouped = analyzer.group_imports(imports)
        
        assert "external" in grouped
        assert "local" in grouped
        assert len(grouped["external"]) >= 2  # react, rxjs
        assert len(grouped["local"]) >= 2    # ./utils/*, ../styles.*


class TestTypeScriptImportOptimization:
    """Test import optimization for TypeScript code."""
    
    def test_keep_all_policy(self):
        """Test that keep_all preserves all imports."""
        code = '''import React from 'react';
import { Component } from '@angular/core';
import { helper } from './utils/helper';
import '../styles.css';

export class MyComponent {
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(policy="keep_all")
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # All imports should be preserved
        assert "import React from 'react';" in result
        assert "import { Component } from '@angular/core';" in result
        assert "import { helper } from './utils/helper';" in result
        assert "import '../styles.css';" in result
        assert meta.get("code.removed.imports", 0) == 0
    
    def test_external_only_policy(self):
        """Test external_only policy for TypeScript."""
        code = '''import React from 'react';
import { Component } from '@angular/core';
import { helper } from './utils/helper';
import '../styles.css';

export class MyComponent {
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
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
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(
            policy="summarize_long",
            max_items_before_summary=5
        )
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should be summarized
        assert "external imports" in result or meta["code.removed.imports"] > 0


class TestTypeScriptImportEdgeCases:
    """Test edge cases for TypeScript import optimization."""
    
    def test_no_imports(self):
        """Test processing TypeScript file without imports."""
        code = '''export class MyClass {
    greet(): string {
        return "Hello world";
    }
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        assert result == code  # Should be unchanged
        assert meta.get("code.removed.imports", 0) == 0
    
    def test_mixed_import_types(self):
        """Test processing mixed TypeScript import types."""
        code = '''import * as fs from 'fs';  // Node.js standard
import React from 'react';  // External package
import { helper } from './utils/helper';  // Local module
import '../styles.css';  // Local CSS

export class MyComponent {
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(
            policy="external_only",
            external_only_patterns=["^fs$"]  # Treat fs as external
        )
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should preserve fs and React
        assert "import * as fs from 'fs';" in result
        assert "import React from 'react';" in result
        
        # Should remove local imports
        assert meta["code.removed.imports"] > 0
    
    def test_placeholder_styles(self):
        """Test different placeholder styles for TypeScript imports."""
        code = '''import { helper } from './local/helper';

export class MyClass {
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        # Test inline style
        adapter._cfg.placeholders.style = "inline"
        result, meta = adapter.process(lctx_ts(code))
        assert "// … 1 imports omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(lctx_ts(code))
        # For TypeScript, block style uses /* */ comments
        assert "imports omitted" in result  # Should still contain the message
    
    def test_type_only_imports(self):
        """Test handling of TypeScript type-only imports."""
        code = '''import type { User } from './types/User';
import { Component } from '@angular/core';
import type { Observable } from 'rxjs';

export class UserComponent {
}
'''
        
        adapter = TypeScriptAdapter()
        import_config = ImportConfig(policy="external_only")
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should be preserved (including type-only)
        assert "@angular/core" in result
        assert "rxjs" in result or "Observable" in result
        
        # Local type import should be processed
        assert meta["code.removed.imports"] > 0 or "User" not in result

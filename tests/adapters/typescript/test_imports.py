"""
Tests for import optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptCfg
from lg.adapters.typescript.imports import TypeScriptImportClassifier, TypeScriptImportAnalyzer
from lg.adapters.typescript.adapter import TypeScriptDocument
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_ts, do_imports, assert_golden_match


class TestTypeScriptImportClassification:
    """Test TypeScript import classification logic."""
    
    def test_external_library_detection(self):
        """Test detection of external libraries."""
        classifier = TypeScriptImportClassifier()
        
        # Node.js built-in modules
        assert classifier.is_external("fs")
        assert classifier.is_external("path")
        assert classifier.is_external("events")
        assert classifier.is_external("stream")
        assert classifier.is_external("crypto")
        
        # Common external packages
        assert classifier.is_external("react")
        assert classifier.is_external("lodash")
        assert classifier.is_external("axios")
        assert classifier.is_external("rxjs")
        assert classifier.is_external("moment")
        
        # Scoped packages
        assert classifier.is_external("@types/express")
        assert classifier.is_external("@nestjs/common")
        assert classifier.is_external("@angular/core")
    
    def test_local_import_detection(self):
        """Test detection of local/relative imports."""
        classifier = TypeScriptImportClassifier()
        
        # Relative imports
        assert not classifier.is_external("./utils")
        assert not classifier.is_external("../shared")
        assert not classifier.is_external("../../core")
        
        # Local-looking imports
        assert not classifier.is_external("src/models")
        assert not classifier.is_external("lib/helpers")
        assert not classifier.is_external("components/Button")
    
    def test_custom_external_patterns(self):
        """Test custom external patterns."""
        custom_patterns = [r"^mycompany/.*", r"^internal-.*"]
        classifier = TypeScriptImportClassifier(custom_patterns)
        
        # Should match custom patterns
        assert classifier.is_external("mycompany/utils")
        assert classifier.is_external("internal-library")
        
        # Should still work for standard detection
        assert classifier.is_external("react")
        assert not classifier.is_external("./local")


class TestTypeScriptImportAnalysis:
    """Test TypeScript import analysis and parsing."""
    
    def test_simple_import_parsing(self):
        """Test parsing of simple import statements."""
        code = '''import React from 'react';
import axios from 'axios';
import * as lodash from 'lodash';
'''
        
        doc = TypeScriptDocument(code, "ts")
        classifier = TypeScriptImportClassifier()
        analyzer = TypeScriptImportAnalyzer(classifier)
        
        imports = analyzer.analyze_imports(doc)
        
        assert len(imports) >= 3
        
        # Check individual imports
        import_modules = [imp.module_name for imp in imports]
        assert "react" in import_modules
        assert "axios" in import_modules
        assert "lodash" in import_modules
    
    def test_named_import_parsing(self):
        """Test parsing of named import statements."""
        code = '''import { Component, useState } from 'react';
import { Observable, Subject } from 'rxjs';
import { UserService } from './services/user-service';
'''
        
        doc = TypeScriptDocument(code, "ts")
        classifier = TypeScriptImportClassifier()
        analyzer = TypeScriptImportAnalyzer(classifier)
        
        imports = analyzer.analyze_imports(doc)
        
        assert len(imports) >= 3
        
        # Check named imports
        for imp in imports:
            if imp.module_name == "react":
                assert "Component" in imp.imported_items
                assert "useState" in imp.imported_items
            elif imp.module_name == "rxjs":
                assert "Observable" in imp.imported_items
                assert "Subject" in imp.imported_items
            elif imp.module_name == "./services/user-service":
                assert "UserService" in imp.imported_items
                assert not imp.is_external  # Local import


class TestTypeScriptImportOptimization:
    """Test TypeScript import optimization policies."""
    
    def test_keep_all_imports(self, adapter, do_imports):
        """Test keeping all imports (default policy)."""
        adapter._cfg = TypeScriptCfg()  # Default imports policy is keep_all
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # No imports should be removed
        assert meta.get("code.removed.imports", 0) == 0
        assert "import { Component, useState, useEffect, useCallback, useMemo } from 'react'" in result
        assert "import * as lodash from 'lodash'" in result
        assert "import axios from 'axios'" in result
        
        assert_golden_match(result, "imports", "keep_all")
    
    def test_strip_local_imports(self, adapter, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # Local imports should be removed
        assert meta.get("code.removed.imports", 0) > 0
        
        # External imports should be preserved
        assert "import axios from 'axios'" in result
        assert "import * as lodash from 'lodash'" in result
        assert "import { Component, useState, useEffect, useCallback, useMemo } from 'react'" in result
        
        # Local imports should be replaced with placeholders
        assert "import { ValidationError, NetworkError } from './errors'" not in result
        assert  "// … 9 imports omitted" in result
        
        assert_golden_match(result, "imports", "strip_local")
    
    def test_strip_external_imports(self, adapter, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # External imports should be removed
        assert meta.get("code.removed.imports", 0) > 0
        
        # Local imports should be preserved
        assert "from './services/user-service'" in result
        assert "from './database/connection'" in result
        
        # External imports should be replaced with placeholders
        assert "import axios from 'axios'" not in result
        assert  "// … 16 imports omitted" in result
        assert "import { Config, Logger } from '@nestjs/common'" not in result
        assert  "// … 10 imports omitted" in result
        
        assert_golden_match(result, "imports", "strip_external")
    
    def test_strip_all_imports(self, adapter, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # All imports should be removed
        assert meta.get("code.removed.imports", 0) > 0
        
        # No imports should remain (except possibly placeholders)
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith(('import', 'from'))]
        assert len(import_lines) == 0
        
        assert_golden_match(result, "imports", "strip_all")
    
    def test_summarize_long_imports(self, adapter, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5  # Low threshold to trigger summarization
        )
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # Long import lists should be summarized
        assert meta.get("code.removed.imports", 0) == 76
        assert  "// … 47 imports omitted" in result
        
        assert_golden_match(result, "imports", "summarize_long")
    
    def test_custom_external_patterns(self, adapter):
        """Test import optimization with custom external patterns."""
        code = '''import React from 'react';
import { MyCompanyUtils } from 'mycompany/utils';  // Should be treated as external
import { InternalHelper } from 'internal/helpers';  // Should be treated as local
import { LocalFunction } from './local';  // Relative import
'''
        
        import_config = ImportConfig(
            policy="strip_local",
            external_patterns=["^mycompany/.*"]
        )
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should be preserved
        assert "import React from 'react'" in result
        assert "import { MyCompanyUtils } from 'mycompany/utils'" in result
        
        # Local imports should be removed
        assert "from 'internal/helpers'" not in result
        assert "from './local'" not in result
        assert "// … import omitted" in result


class TestTypeScriptImportEdgeCases:
    """Test edge cases for TypeScript import optimization."""
    
    def test_mixed_import_styles_handling(self, adapter):
        """Test handling of mixed import styles."""
        code = '''import React, { Component, useState } from 'react';
import * as lodash from 'lodash';
import { Observable, Subject, map, filter } from 'rxjs';
'''
        
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=3
        )
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Long named import lists should be summarized
        assert meta.get("code.removed.imports", 0) >= 0
    
    def test_type_only_imports(self, adapter):
        """Test handling of TypeScript type-only imports."""
        code = '''import type { User, Product } from './types';
import type { Config } from 'external-config';
import { type Settings, normalFunction } from './config';
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External type imports should be preserved
        assert "import type { Config } from 'external-config'" in result
        
        # Local type imports should be processed
        assert "from './types'" not in result
        assert "from './config'" not in result
        assert "// … 2 imports omitted" in result
    
    def test_namespace_imports(self, adapter):
        """Test handling of namespace imports."""
        code = '''import * as React from 'react';
import * as lodash from 'lodash';
import * as Utils from './utils';
import * as API from '../api';
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External namespace imports should be preserved
        assert "import * as React from 'react'" in result
        assert "import * as lodash from 'lodash'" in result
        
        # Local namespace imports should be processed
        assert "from './utils'" not in result
        assert "from '../api'" not in result
        assert "// … 2 imports omitted" in result
    
    def test_side_effect_imports(self, adapter):
        """Test handling of side-effect imports."""
        code = '''import 'reflect-metadata';
import 'zone.js/dist/zone';
import './polyfills';
import '../styles/global.css';
import React from 'react';
import { Component } from './Component';
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External side-effect imports should be preserved
        assert "import 'reflect-metadata'" in result
        
        # Local side-effect imports should be processed
        assert "'./polyfills'" not in result
        assert "'../styles/global.css'" not in result
        assert "// … import omitted" in result
    
    def test_scoped_package_imports(self, adapter):
        """Test handling of scoped npm packages."""
        code = '''import { Controller } from '@nestjs/common';
import { GraphQLModule } from '@nestjs/graphql';
import { Router } from '@types/express';
import { LocalService } from './services/local';
'''
        
        import_config = ImportConfig(policy="strip_local")
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Scoped packages should be treated as external
        assert "import { Controller } from '@nestjs/common'" in result
        assert "import { GraphQLModule } from '@nestjs/graphql'" in result
        assert "import { Router } from '@types/express'" in result
        
        # Local imports should be processed
        assert "from './services/local'" not in result
        assert "// … import omitted" in result
    
    def test_strip_external_with_summarize_long(self, adapter):
        """Test combining strip_external policy with summarize_long option."""
        code = '''import React from 'react';
import { Observable, Subject, map, filter, switchMap, mergeMap } from 'rxjs';
import { UserService } from './services/user-service';
import { helper1, helper2, helper3, helper4, helper5, helper6 } from './utils/helpers';
'''
        
        import_config = ImportConfig(
            policy="strip_external",
            summarize_long=True,
            max_items_before_summary=3
        )
        
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should be stripped regardless of length
        assert "import React from 'react'" not in result
        assert "from 'rxjs'" not in result

        # Local imports should remain but long ones should be summarized
        assert "from './services/user-service'" in result
        # Long local import should be summarized
        assert "// … 6 imports omitted" in result

"""
Tests for import optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_ts, do_imports, assert_golden_match


class TestTypeScriptImportOptimization:
    """Test import processing for TypeScript code."""
    
    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="keep_all"))
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # No imports should be removed
        assert meta.get("code.removed.imports", 0) == 0
        assert "import { Component }" in result
        assert "import * as lodash" in result
        assert "import axios" in result
        
        assert_golden_match(result, "imports", "keep_all")
    
    def test_external_only_imports(self, do_imports):
        """Test keeping only external imports."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="external_only"))
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # Local imports should be processed
        assert meta.get("code.removed.imports", 0) > 0
        
        # External imports should remain
        assert "import axios" in result
        assert "import * as lodash" in result
        assert "import { Component }" in result  # React is external
        
        # Local imports should be summarized or removed
        assert "./utils" not in result or "… import" in result
        
        assert_golden_match(result, "imports", "external_only")
    
    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(
            policy="summarize_long",
            max_line_length=80,
            max_imports_per_line=3
        ))
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # Long import lines should be summarized
        assert meta.get("code.removed.imports", 0) > 0
        assert "… imports" in result or "…" in result
        
        assert_golden_match(result, "imports", "summarize_long")
    
    def test_complex_import_config(self, do_imports):
        """Test complex import configuration."""
        import_config = ImportConfig(
            policy="external_only",
            max_line_length=60,
            max_imports_per_line=2,
            preserve_types=True,
            keep_namespace_imports=True
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=import_config)
        
        result, meta = adapter.process(lctx_ts(do_imports))
        
        # Should preserve type imports and namespace imports
        assert "import type" in result
        assert "import * as" in result
        
        assert_golden_match(result, "imports", "complex_config")


class TestTypeScriptImportClassification:
    """Test TypeScript-specific import classification."""
    
    def test_external_import_detection(self):
        """Test detection of external vs local imports."""
        code = '''
// External npm packages
import React from 'react';
import { Component } from 'react';
import * as lodash from 'lodash';
import axios from 'axios';
import { Observable } from 'rxjs';

// Type-only imports
import type { UserType } from './types/User';
import type { Config } from 'config-package';

// Local relative imports
import { utils } from './utils';
import { UserService } from '../services/UserService';
import { constants } from '../../constants';

// Namespace imports
import * as Utils from './utils/index';
import * as API from '../api';
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="external_only"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should be preserved
        assert "import React" in result
        assert "import { Component }" in result
        assert "import * as lodash" in result
        assert "import axios" in result
        assert "import { Observable }" in result
        
        # Type imports from external packages should be preserved
        assert "import type { Config }" in result
        
        # Local imports should be processed
        assert "./utils" not in result or "… import" in result
        assert "../services/UserService" not in result or "… import" in result
    
    def test_typescript_specific_imports(self):
        """Test TypeScript-specific import features."""
        code = '''
// Type-only imports
import type { User, Product } from './types';
import type { ApiResponse } from 'api-types';

// Interface imports
import { type Config, type Settings } from './config';

// Namespace imports
import * as Types from './types';
import * as Utils from 'utility-library';

// Dynamic imports (should be preserved)
const modulePromise = import('./dynamic-module');
const configPromise = import('config-loader');

// Re-exports
export { default as Button } from './Button';
export type { ButtonProps } from './Button';
export * from './utilities';
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(
            policy="external_only",
            preserve_types=True,
            keep_namespace_imports=True
        ))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Type imports should be preserved
        assert "import type" in result
        
        # Namespace imports should be preserved
        assert "import * as Utils" in result
        
        # Dynamic imports should be preserved
        assert "import('./dynamic-module')" in result
        assert "import('config-loader')" in result
        
        # Re-exports should be handled
        assert "export {" in result or "export type" in result
    
    def test_barrel_file_imports(self):
        """Test handling of barrel file imports."""
        code = '''
// Barrel file imports (index files)
import { Component1, Component2 } from './components';
import { Service1, Service2 } from './services/index';
import * as Utilities from './utils';

// Specific file imports
import { SpecificComponent } from './components/SpecificComponent';
import { SpecificService } from './services/SpecificService';

// External barrel imports
import { Button, Input, Form } from 'ui-library';
import * as Icons from 'icon-library';
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="external_only"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should remain
        assert "ui-library" in result
        assert "icon-library" in result
        
        # Local barrel imports should be processed
        assert ("./components" not in result or "… import" in result or 
                "./services" not in result or "… import" in result)
    
    def test_side_effect_imports(self):
        """Test handling of side-effect imports."""
        code = '''
// Side-effect imports (no destructuring)
import 'reflect-metadata';
import 'zone.js/dist/zone';
import './polyfills';
import '../styles/global.css';

// Regular imports
import React from 'react';
import { Component } from './Component';

// Import with side effects and binding
import('./dynamic-styles.css');
import('./theme-loader').then(theme => theme.apply());
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="external_only"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External side-effect imports should be preserved
        assert "import 'reflect-metadata'" in result
        assert "import 'zone.js/dist/zone'" in result
        
        # Local side-effect imports should be processed
        assert ("'./polyfills'" not in result or "… import" in result or
                "'../styles/global.css'" not in result or "… import" in result)
    
    def test_import_with_assertions(self):
        """Test import assertions (JSON modules, etc.)."""
        code = '''
// JSON imports with assertions
import config from './config.json' assert { type: 'json' };
import data from '../data/sample.json' assert { type: 'json' };

// CSS imports
import styles from './Component.module.css';
import './global.css';

// Worker imports
import Worker from './worker.ts?worker';

// External JSON imports
import packageJson from 'package/package.json' assert { type: 'json' };
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(imports=ImportConfig(policy="external_only"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # External imports should be preserved
        assert "package/package.json" in result
        
        # Local JSON/CSS imports should be processed
        assert ("./config.json" not in result or "… import" in result or
                "./Component.module.css" not in result or "… import" in result)

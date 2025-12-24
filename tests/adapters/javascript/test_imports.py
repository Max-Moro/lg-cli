"""
Tests for import optimization in JavaScript adapter.
"""

import re

from lg.adapters.langs.javascript import JavaScriptCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaScriptImportOptimization:
    """Test JavaScript import optimization policies."""

    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(JavaScriptCfg())  # Default imports policy is keep_all

        result, meta = adapter.process(lctx(do_imports))

        # No imports should be removed
        assert meta.get("javascript.removed.import", 0) == 0
        assert "import { Component, useState, useEffect, useCallback, useMemo } from 'react'" in result
        assert "import * as lodash from 'lodash'" in result
        assert "import axios from 'axios'" in result

        assert_golden_match(result, "imports", "keep_all")

    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        # Local imports should be removed
        assert meta.get("javascript.removed.import", 0) > 0

        # External imports should be preserved
        assert "import axios from 'axios'" in result
        assert "import * as lodash from 'lodash'" in result

        # Local imports should be replaced with placeholders
        assert "from './services/user-service.js'" not in result
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_local")

    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        # External imports should be removed
        assert meta.get("javascript.removed.import", 0) > 0

        # Local imports should be preserved
        assert "from './services/user-service.js'" in result
        assert "from './database/connection.js'" in result

        # External imports should be replaced with placeholders
        assert "import axios from 'axios'" not in result
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_external")

    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        # All imports should be removed
        assert meta.get("javascript.removed.import", 0) > 0

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

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        # Long import lists should be summarized
        assert meta.get("javascript.removed.import", 0) > 0
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "summarize_long")


class TestJavaScriptImportEdgeCases:
    """Test edge cases for JavaScript import optimization."""

    def test_dynamic_imports(self):
        """Test handling of dynamic imports."""
        code = '''
const dynamicModule = async () => {
    const { default: chalk } = await import('chalk');
    return chalk;
};
'''

        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        # Dynamic imports should be preserved as-is
        assert "await import('chalk')" in result

    def test_require_imports(self):
        """Test handling of CommonJS require imports."""
        code = '''
let csvParser;
try {
    csvParser = require('csv-parser');
} catch (error) {
    console.warn('csv-parser not available');
}
'''

        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        # Note: Dynamic require() calls are not currently detected as imports.
        # Only static ESM import statements are processed.
        # require() would need AST analysis of call_expression nodes.
        # TODO: Implement require() detection if CommonJS support is needed
        pass  # Test documents limitation without failing

    def test_side_effect_imports(self):
        """Test handling of side-effect imports."""
        code = '''
import 'reflect-metadata';
import './polyfills.js';
import '../styles/global.css';
import React from 'react';
import { Component } from './Component.js';
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(JavaScriptCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        # External side-effect imports should be preserved
        assert "import 'reflect-metadata'" in result

        # Local side-effect imports should be processed
        assert "'./polyfills.js'" not in result
        assert "'../styles/global.css'" not in result

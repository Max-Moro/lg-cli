"""
Tests for import optimization in Rust adapter.
"""

import re

from lg.adapters.langs.rust import RustCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestRustImportOptimization:
    """Test Rust import optimization policies."""

    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(RustCfg())

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("rust.removed.import", 0) == 0
        assert "use std::io" in result
        assert "use std::collections" in result and "HashMap" in result

        assert_golden_match(result, "imports", "keep_all", language="rust")

    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("rust.removed.import", 0) > 0

        assert "use std::io" in result
        assert "use serde::" in result

        assert "use crate::models::User" not in result
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_local", language="rust")

    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("rust.removed.import", 0) > 0

        assert "use crate::models::User" in result

        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_external", language="rust")

    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("rust.removed.import", 0) > 0

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith('use')]
        assert len(import_lines) < 10

        assert_golden_match(result, "imports", "strip_all", language="rust")

    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5
        )

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("rust.removed.import", 0) > 0
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "summarize_long", language="rust")


class TestRustImportEdgeCases:
    """Test edge cases for Rust import optimization."""

    def test_std_vs_external_crates(self):
        """Test distinction between std library and external crates."""
        code = '''use std::io::{self, Read, Write};
use std::collections::{HashMap, HashSet};
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::runtime::Runtime;
use reqwest::Client;

use crate::models::User;
use crate::services::UserService;
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "use std::io::{self, Read, Write}" in result
        assert "use serde::{Deserialize, Serialize}" in result
        assert "use tokio::runtime::Runtime" in result

        assert "use crate::models::User" not in result
        assert "use crate::services::UserService" not in result

    def test_import_aliases(self):
        """Test handling of import aliases."""
        code = '''use std::collections::HashMap as Map;
use std::sync::Arc;

use chrono::DateTime as ChronoDateTime;

use crate::models::User as UserModel;
use super::helpers::format_name;
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "use std::collections::HashMap as Map" in result
        assert "use chrono::DateTime as ChronoDateTime" in result

        assert "use crate::models::User as UserModel" not in result
        assert "use super::helpers::format_name" not in result

    def test_glob_imports(self):
        """Test handling of glob imports."""
        code = '''use std::io::prelude::*;
use std::collections::*;

use serde::*;

use crate::models::*;
use super::*;
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "use std::io::prelude::*" in result
        assert "use serde::*" in result

        assert "use crate::models::*" not in result
        assert "use super::*" not in result

    def test_nested_imports(self):
        """Test handling of nested imports."""
        code = '''use std::io::{
    self,
    Read,
    Write,
    BufReader,
    BufWriter,
};

use crate::{
    models::{User, Post, Comment},
    services::{UserService, PostService},
    utils::validators,
};
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "use std::io::{" in result

        assert "use crate::{" not in result

    def test_pub_use_reexports(self):
        """Test handling of pub use re-exports."""
        code = '''pub use std::collections::HashMap;
pub use serde::{Deserialize, Serialize};

pub use crate::models::User;
pub use super::helpers::format_name;
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(RustCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "pub use std::collections::HashMap" in result
        assert "pub use serde::{Deserialize, Serialize}" in result

        assert "pub use crate::models::User" not in result

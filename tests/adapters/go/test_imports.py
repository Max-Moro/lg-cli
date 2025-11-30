"""
Tests for import optimization in Go adapter.
"""

from lg.adapters.go import GoCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestGoImportOptimization:
    """Test Go import optimization policies."""

    def test_keep_all_imports(self, do_imports):
        """Test keeping all imports (default policy)."""
        adapter = make_adapter(GoCfg())

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("go.removed.imports", 0) == 0
        assert 'import "fmt"' in result
        assert 'import "os"' in result

        assert_golden_match(result, "imports", "keep_all", language="go")

    def test_strip_local_imports(self, do_imports):
        """Test stripping local imports (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("go.removed.import", 0) > 0

        assert 'import "fmt"' in result
        assert '"github.com/pkg/errors"' in result

        assert '"myproject/internal/utils"' not in result
        assert "// … imports omitted" in result

        assert_golden_match(result, "imports", "strip_local", language="go")

    def test_strip_external_imports(self, do_imports):
        """Test stripping external imports (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("go.removed.import", 0) > 0

        assert '"myproject/internal/utils"' in result

        assert "// … " in result and "omitted" in result

        assert_golden_match(result, "imports", "strip_external", language="go")

    def test_strip_all_imports(self, do_imports):
        """Test stripping all imports."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("go.removed.import", 0) > 0

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        import_lines = [line for line in lines if line.startswith('import')]
        assert len(import_lines) < 10

        assert_golden_match(result, "imports", "strip_all", language="go")

    def test_summarize_long_imports(self, do_imports):
        """Test summarizing long import lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5
        )

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("go.removed.import", 0) > 0
        assert "// … " in result and "imports omitted" in result

        assert_golden_match(result, "imports", "summarize_long", language="go")


class TestGoImportEdgeCases:
    """Test edge cases for Go import optimization."""

    def test_standard_library_vs_third_party(self):
        """Test distinction between standard library and third-party imports."""
        code = '''package main

import (
    "fmt"
    "os"
    "net/http"

    "github.com/gorilla/mux"
    "github.com/lib/pq"

    "myproject/internal/db"
    "myproject/pkg/utils"
)
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert '"fmt"' in result
        assert '"os"' in result
        assert '"github.com/gorilla/mux"' in result

        assert '"myproject/internal/db"' not in result
        assert '"myproject/pkg/utils"' not in result

    def test_import_aliases(self):
        """Test handling of import aliases."""
        code = '''package main

import (
    stdlog "log"

    golog "github.com/sirupsen/logrus"

    mylog "myproject/internal/logger"
)
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert 'stdlog "log"' in result
        assert 'golog "github.com/sirupsen/logrus"' in result

        assert 'mylog "myproject/internal/logger"' not in result

    def test_dot_imports(self):
        """Test handling of dot imports."""
        code = '''package main

import (
    . "fmt"
    . "testing"

    . "myproject/internal/testutils"
)
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert '. "fmt"' in result
        assert '. "testing"' in result

        assert '. "myproject/internal/testutils"' not in result

    def test_blank_imports(self):
        """Test handling of blank imports (side effects)."""
        code = '''package main

import (
    _ "database/sql"
    _ "github.com/lib/pq"

    _ "myproject/internal/migrations"
)
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(GoCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert '_ "database/sql"' in result
        assert '_ "github.com/lib/pq"' in result

        assert '_ "myproject/internal/migrations"' not in result

"""
Tests for include optimization in C adapter.
"""

import re

from lg.adapters.langs.c import CCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCImportOptimization:
    """Test C include optimization policies."""

    def test_keep_all_includes(self, do_imports):
        """Test keeping all includes (default policy)."""
        adapter = make_adapter(CCfg())

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("c.removed.import", 0) == 0
        assert "#include <stdio.h>" in result
        assert "#include <stdlib.h>" in result

        assert_golden_match(result, "imports", "keep_all")

    def test_strip_local_includes(self, do_imports):
        """Test stripping local includes (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("c.removed.import", 0) > 0

        assert "#include <stdio.h>" in result
        assert "#include <curl/curl.h>" in result

        assert '"services/user_service.h"' not in result
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_local")

    def test_strip_external_includes(self, do_imports):
        """Test stripping external includes (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("c.removed.import", 0) > 0

        assert '"services/user_service.h"' in result

        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_external")

    def test_strip_all_includes(self, do_imports):
        """Test stripping all includes."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("c.removed.import", 0) > 0

        lines = [line.strip() for line in result.split('\n') if line.strip()]
        include_lines = [line for line in lines if line.startswith('#include')]
        assert len(include_lines) < 10

        assert_golden_match(result, "imports", "strip_all")

    def test_summarize_long_includes(self, do_imports):
        """Test summarizing long include lists."""
        import_config = ImportConfig(
            policy="keep_all",
            summarize_long=True,
            max_items_before_summary=5
        )

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("c.removed.import", 0) > 0
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "summarize_long")


class TestCImportEdgeCases:
    """Test edge cases for C include optimization."""

    def test_system_vs_local_headers(self):
        """Test distinction between system and local headers."""
        code = '''#include <stdio.h>
#include <stdlib.h>
#include "local_header.h"
#include "utils/helper.h"

int main(void) {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "#include <stdio.h>" in result
        assert "#include <stdlib.h>" in result

        assert '"local_header.h"' not in result
        assert '"utils/helper.h"' not in result

    def test_posix_headers(self):
        """Test handling of POSIX headers as external."""
        code = '''#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include "local.h"

int main(void) {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "#include <unistd.h>" in result
        assert "#include <sys/types.h>" in result
        assert '"local.h"' not in result

    def test_external_library_headers(self):
        """Test recognition of external library headers."""
        code = '''#include <curl/curl.h>
#include <sqlite3.h>
#include <openssl/ssl.h>
#include "mylib/module.h"

int main(void) {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(CCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert '"mylib/module.h"' in result

        assert "<curl/curl.h>" not in result
        assert "<sqlite3.h>" not in result

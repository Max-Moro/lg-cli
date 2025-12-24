"""
Tests for include optimization in C++ adapter.
"""

import re

from lg.adapters.langs.cpp import CppCfg
from lg.adapters.code_model import ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCppImportOptimization:
    """Test C++ include optimization policies."""

    def test_keep_all_includes(self, do_imports):
        """Test keeping all includes (default policy)."""
        adapter = make_adapter(CppCfg())

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("cpp.removed.import", 0) == 0
        assert "#include <iostream>" in result
        assert "#include <vector>" in result

        assert_golden_match(result, "imports", "keep_all")

    def test_strip_local_includes(self, do_imports):
        """Test stripping local includes (keeping external)."""
        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("cpp.removed.import", 0) > 0

        assert "#include <iostream>" in result
        assert "#include <boost/algorithm/string.hpp>" in result

        assert '"services/user_service.h"' not in result
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_local")

    def test_strip_external_includes(self, do_imports):
        """Test stripping external includes (keeping local)."""
        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("cpp.removed.import", 0) > 0

        assert '"services/user_service.hpp"' in result

        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "strip_external")

    def test_strip_all_includes(self, do_imports):
        """Test stripping all includes."""
        import_config = ImportConfig(policy="strip_all")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("cpp.removed.import", 0) > 0

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

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(do_imports))

        assert meta.get("cpp.removed.import", 0) > 0
        assert re.search(r'// … (\d+ )?imports? omitted', result)

        assert_golden_match(result, "imports", "summarize_long")


class TestCppImportEdgeCases:
    """Test edge cases for C++ include optimization."""

    def test_system_vs_local_headers(self):
        """Test distinction between system and local headers."""
        code = '''#include <iostream>
#include <vector>
#include "local_header.h"
#include "utils/helper.h"

int main() {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "#include <iostream>" in result
        assert "#include <vector>" in result

        assert '"local_header.h"' not in result
        assert '"utils/helper.h"' not in result

    def test_standard_library_headers(self):
        """Test handling of standard library headers as external."""
        code = '''#include <algorithm>
#include <memory>
#include <unordered_map>
#include "local.h"

int main() {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "#include <algorithm>" in result
        assert "#include <unordered_map>" in result
        assert '"local.h"' not in result

    def test_external_library_headers(self):
        """Test recognition of external library headers."""
        code = '''#include <boost/algorithm/string.hpp>
#include <nlohmann/json.hpp>
#include <openssl/ssl.h>
#include "mylib/module.h"

int main() {
    return 0;
}
'''

        import_config = ImportConfig(policy="strip_external")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert '"mylib/module.h"' in result

        assert "<boost/algorithm/string.hpp>" not in result
        assert "<nlohmann/json.hpp>" not in result

    def test_forward_declarations(self):
        """Test that forward declarations are not treated as includes."""
        code = '''#include <memory>

class User;
class Service;
namespace detail { class Impl; }

#include "local.h"

std::unique_ptr<User> createUser();
'''

        import_config = ImportConfig(policy="strip_local")

        adapter = make_adapter(CppCfg(imports=import_config))

        result, meta = adapter.process(lctx(code))

        assert "class User;" in result
        assert "class Service;" in result
        assert "namespace detail" in result
        assert "#include <memory>" in result
        assert '"local.h"' not in result

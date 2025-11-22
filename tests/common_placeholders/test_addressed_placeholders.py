"""
Tests for addressed section placeholders.

Checks cross-scope reference functionality:
- ${@origin:section-name} - classic format
- ${@[origin]:section-name} - bracketed format for origins with colons
- Federated projects and multiple scopes
- Addressing error handling
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    federated_project,
    create_template, render_template
)


def test_simple_addressed_section_placeholder(federated_project):
    """Test simple addressed placeholders ${@origin:section}."""
    root = federated_project

    # Create template with addressed links
    create_template(root, "addressed-test", """# Addressed Test

## Root Project Overview

${overview}

## Web Application Source

${@apps/web:web-src}

## Core Library

${@libs/core:core-lib}
""")

    result = render_template(root, "ctx:addressed-test")

    # Check content from root section
    assert "Federated Project" in result
    assert "Project Overview" in result

    # Check content from apps/web
    assert "export const App" in result
    assert "export function webUtil" in result

    # Check content from libs/core
    assert "class Processor:" in result


def test_bracketed_addressed_section_placeholder(federated_project):
    """Test bracketed addressed placeholders ${@[origin]:section}."""
    root = federated_project

    # Create template with bracketed addressing
    create_template(root, "bracketed-test", """# Bracketed Test

## Web App (bracketed syntax)

${@[apps/web]:web-src}

## Core Lib (bracketed syntax)

${@[libs/core]:core-lib}
""")

    result = render_template(root, "ctx:bracketed-test")

    # Content should be identical to regular addressing
    assert "export const App" in result
    assert "class Processor:" in result


def test_mixed_local_and_addressed_placeholders(federated_project):
    """Test mixed local and addressed placeholders."""
    root = federated_project

    create_template(root, "mixed-test", """# Mixed Test

## Local Root Sections

${overview}
${root-config}

## External Web Sections

${@apps/web:web-src}
${@apps/web:web-docs}

## External Core Sections

${@libs/core:core-lib}
${@libs/core:core-api}
""")

    result = render_template(root, "ctx:mixed-test")

    # Local sections
    assert "Federated Project" in result

    # Web sections
    assert "export const App" in result
    assert "Deployment instructions" in result

    # Core sections - regular and API (with stripped function bodies)
    assert "class Processor:" in result
    assert "def get_client():" in result


def test_addressed_placeholder_nonexistent_scope_error(federated_project):
    """Test error when referencing a nonexistent scope."""
    root = federated_project

    create_template(root, "bad-scope-test", """# Bad Scope Test

${@nonexistent/module:some-section}
""")

    # Should raise error about nonexistent scope
    with pytest.raises(TemplateProcessingError, match=r"Child lg-cfg not found"):
        render_template(root, "ctx:bad-scope-test")


def test_addressed_placeholder_nonexistent_section_error(federated_project):
    """Test error when referencing a nonexistent section in an existing scope."""
    root = federated_project

    create_template(root, "bad-section-test", """# Bad Section Test

${@apps/web:nonexistent-section}
""")

    # Should raise error about nonexistent section
    with pytest.raises(TemplateProcessingError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:bad-section-test")


def test_addressed_placeholder_complex_paths(federated_project):
    """Test addressed placeholders with complex paths."""
    root = federated_project

    # Create nested scope structure
    from .conftest import create_sections_yaml, write_source_file

    # Deeply nested scope
    deep_sections = {
        "deep-section": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/deep/**"]
            }
        }
    }
    create_sections_yaml(root / "libs" / "core" / "modules" / "auth", deep_sections)

    write_source_file(root / "libs" / "core" / "modules" / "auth" / "deep" / "security.py",
                     "def authenticate(): pass", "python")

    create_template(root, "complex-paths-test", """# Complex Paths Test

## Deep Auth Module

${@libs/core/modules/auth:deep-section}
""")

    result = render_template(root, "ctx:complex-paths-test")

    assert "def authenticate(): pass" in result


def test_multiple_addressed_placeholders_same_scope(federated_project):
    """Test multiple addressed placeholders from the same scope."""
    root = federated_project

    create_template(root, "multiple-same-scope-test", """# Multiple Same Scope Test

## Web Source Code

${@apps/web:web-src}

## Web Documentation

${@apps/web:web-docs}

## Web Source Code Again

${@apps/web:web-src}
""")

    result = render_template(root, "ctx:multiple-same-scope-test")

    # Content of web-src should appear twice
    occurrences = result.count("export const App")
    assert occurrences == 2

    # Content of web-docs should appear once
    occurrences = result.count("Deployment instructions")
    assert occurrences == 1


def test_deeply_nested_federated_scopes(tmp_path):
    """
    Test deep nesting of federated scopes (3+ levels).

    Structure:
    root/
      lg-cfg/
        root-ctx.ctx.md → ${ctx@level1:level1-ctx}
      level1/
        lg-cfg/
          level1-ctx.ctx.md → ${tpl:level1-tpl} + ${ctx@level2:level2-ctx}
          level1-tpl.tpl.md → "LEVEL1 TEMPLATE"
        level2/
          lg-cfg/
            level2-ctx.ctx.md → ${tpl:level2-tpl} + ${md@level3:doc}
            level2-tpl.tpl.md → "LEVEL2 TEMPLATE"
          level3/
            lg-cfg/
              doc.md → "LEVEL3 DOCUMENT"
    """
    from .conftest import write, create_sections_yaml

    root = tmp_path

    # === Root level ===
    create_sections_yaml(root, {})
    create_template(root, "root-ctx", """# Root Context

${ctx@level1:level1-ctx}
""")

    # === Level 1 (level1/) ===
    create_sections_yaml(root / "level1", {})
    create_template(root / "level1", "level1-tpl", "LEVEL1 TEMPLATE\n", "tpl")
    create_template(root / "level1", "level1-ctx", """# Level1 Context

${tpl:level1-tpl}

${ctx@level2:level2-ctx}
""")

    # === Level 2 (level1/level2/) ===
    create_sections_yaml(root / "level1" / "level2", {})
    create_template(root / "level1" / "level2", "level2-tpl", "LEVEL2 TEMPLATE\n", "tpl")
    create_template(root / "level1" / "level2", "level2-ctx", """# Level2 Context

${tpl:level2-tpl}

${md@level3:doc}
""")

    # === Level 3 (level1/level2/level3/) ===
    # Create structure for level3 inside level1/level2
    level3_root = root / "level1" / "level2" / "level3"
    create_sections_yaml(level3_root, {})
    write(
        level3_root / "lg-cfg" / "doc.md",
        "LEVEL3 DOCUMENT\n"
    )

    # Render root context
    result = render_template(root, "ctx:root-ctx")

    # Check that all levels resolved correctly
    assert "LEVEL1 TEMPLATE" in result, "Level1 template not found"
    assert "LEVEL2 TEMPLATE" in result, "Level2 template not found"
    assert "LEVEL3 DOCUMENT" in result, "Level3 document not found"

    # Check order (nesting should be preserved)
    level1_pos = result.find("LEVEL1 TEMPLATE")
    level2_pos = result.find("LEVEL2 TEMPLATE")
    level3_pos = result.find("LEVEL3 DOCUMENT")

    assert level1_pos < level2_pos < level3_pos, \
        "Nesting order violated"


@pytest.mark.parametrize("origin,section,expected_content", [
    ("apps/web", "web-src", "export const App"),
    ("apps/web", "web-docs", "Deployment instructions"),
    ("libs/core", "core-lib", "class Processor:"),
    ("libs/core", "core-api", "def get_client():")
])
def test_addressed_placeholder_parametrized(federated_project, origin, section, expected_content):
    """Parametrized test of various addressed placeholders."""
    root = federated_project

    create_template(root, f"param-test-{origin.replace('/', '-')}-{section}", f"""# Param Test

${{@{origin}:{section}}}
""")

    result = render_template(root, f"ctx:param-test-{origin.replace('/', '-')}-{section}")
    assert expected_content in result


def test_addressed_placeholder_deep_nesting(federated_project):
    """Test deep nesting of addressed links."""
    root = federated_project

    # Create deep module structure
    from .conftest import create_sections_yaml, write_source_file

    # Four levels of nesting
    deep_path = root / "libs" / "core" / "modules" / "data" / "processors" / "advanced"

    deep_sections = {
        "advanced-processor": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/advanced/**"]
            }
        }
    }
    create_sections_yaml(deep_path, deep_sections)

    write_source_file(deep_path / "advanced" / "ml.py",
                     "class MLProcessor: pass", "python")

    create_template(root, "deep-nesting-test", """# Deep Nesting Test

${@libs/core/modules/data/processors/advanced:advanced-processor}
""")

    result = render_template(root, "ctx:deep-nesting-test")

    assert "class MLProcessor: pass" in result
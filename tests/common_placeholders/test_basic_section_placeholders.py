"""
Tests for basic section placeholders.

Checks main functionality of inserting ${section-name}:
- Simple section insertions
- Sections from fragments (*.sec.yaml)
- Error handling
- Multiple placeholders in a single template
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, multilang_project, fragments_project,
    create_template, render_template
)


def test_simple_section_placeholder(basic_project):
    """Test simple section insertion ${src}."""
    root = basic_project

    # Create template with simple section placeholder
    create_template(root, "simple-test", """# Test Template

## Source Code

${src}

End of template.
""")

    result = render_template(root, "ctx:simple-test")

    # Check that src section content is inserted
    assert "Source Code" in result
    assert "Source file: main.py" in result
    assert "def main():" in result
    assert "Source file: utils.py" in result
    assert "def helper_function(x):" in result
    assert "End of template." in result


def test_section_placeholder_with_different_sections(basic_project):
    """Test insertion of different sections in one template."""
    root = basic_project

    create_template(root, "multi-section-test", """# Multi-Section Test

## Documentation

${docs}

## Source Code

${src}

## Test Suite

${tests}
""")

    result = render_template(root, "ctx:multi-section-test")

    # Check content from docs section
    assert "Project Documentation" in result
    assert "API Reference" in result

    # Check content from src section
    assert "def main():" in result
    assert "def helper_function(x):" in result

    # Check content from tests section
    assert "def test_main():" in result
    assert "def test_helper():" in result


def test_section_placeholder_with_fragments(fragments_project):
    """Test insertion of sections from fragments *.sec.yaml."""
    root = fragments_project

    create_template(root, "fragments-test", """# Fragments Test

## Main Module

${main}

## Database Layer

${database}

## Security: Authentication

${security/auth}

## Security: Permissions

${security/permissions}

## API v1

${api/api-v1}
""")

    result = render_template(root, "ctx:fragments-test")

    # Check main section
    assert "print('main')" in result

    # Check section from single fragment
    assert "class User: pass" in result

    # Check sections from multi-section fragment
    assert "def login(): pass" in result
    assert "def check(): pass" in result

    # Check section from subdirectory
    assert "def handle(): pass" in result


def test_section_placeholder_not_found_error(basic_project):
    """Test error handling when section is not found."""
    root = basic_project

    create_template(root, "notfound-test", """# Not Found Test

${nonexistent-section}
""")

    # Should raise error that section is not found
    with pytest.raises(TemplateProcessingError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:notfound-test")


def test_section_placeholder_empty_section(basic_project):
    """Test handling of empty section (without files)."""
    root = basic_project

    # Create section that finds no files
    from .conftest import create_sections_yaml

    sections_config = {
        "empty-section": {
            "extensions": [".nonexistent"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        }
    }

    # Extend existing configuration
    existing_config = {
        "src": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        }
    }
    existing_config.update(sections_config)
    create_sections_yaml(root, existing_config)

    create_template(root, "empty-test", """# Empty Test

Before empty section.

${empty-section}

After empty section.
""")

    result = render_template(root, "ctx:empty-test")

    # Empty section should be skipped
    assert "Before empty section." in result
    assert "After empty section." in result
    # There should be no additional content between them except separators


def test_section_placeholder_preserves_code_fencing(multilang_project):
    """Test preservation of code fencing for different languages."""
    root = multilang_project

    create_template(root, "fencing-test", """# Code Fencing Test

## Python Code

${python-src}

## TypeScript Code

${typescript-src}

## Documentation (no fencing)

${shared-docs}
""")

    result = render_template(root, "ctx:fencing-test")

    # Check that Python code is wrapped in fenced blocks
    assert "```python" in result
    assert "class Core:" in result

    # Check that TypeScript code is wrapped in fenced blocks
    assert "```typescript" in result or "```ts" in result
    assert "export class App" in result

    assert "Architecture Overview" in result
    # Should not have fenced blocks around documentation
    lines = result.split('\n')
    md_context = []
    in_md_section = False
    for line in lines:
        if "Architecture Overview" in line:
            in_md_section = True
        if in_md_section:
            md_context.append(line)
            if line.startswith("## Frontend (TypeScript)"):
                break

    # Documentation should not be in fenced block
    md_text = '\n'.join(md_context)
    assert "```" not in md_text or md_text.count("```") == 0


def test_multiple_same_section_placeholders(basic_project):
    """Test multiple references to the same section."""
    root = basic_project

    create_template(root, "duplicate-test", """# Duplicate Test

## First Reference

${src}

## Some Text Between

This is some intermediate content.

## Second Reference

${src}

## End
""")

    result = render_template(root, "ctx:duplicate-test")

    # Section content should appear twice
    occurrences = result.count("def main():")
    assert occurrences == 2

    occurrences = result.count("def helper_function(x):")
    assert occurrences == 2

    # Intermediate text should be present
    assert "This is some intermediate content." in result


def test_section_placeholder_whitespace_handling(basic_project):
    """Test whitespace handling around section placeholders."""
    root = basic_project

    create_template(root, "whitespace-test", """# Whitespace Test

Before placeholder.
${src}
After placeholder.

Indented:
    ${docs}
End.
""")

    result = render_template(root, "ctx:whitespace-test")

    # Check correct insertion without formatting violations
    assert "Before placeholder." in result
    assert "After placeholder." in result
    assert "End." in result

    # Content from sections should be present
    assert "def main():" in result
    assert "Project Documentation" in result


def test_section_placeholder_in_nested_structure(basic_project):
    """Test section placeholders in nested structure of lists and quotes."""
    root = basic_project

    create_template(root, "nested-test", """# Nested Test

## Code Examples

1. Main module:
   ${src}

2. Documentation:
   > ${docs}

3. Tests:
   - Unit tests: ${tests}
   - Integration tests: coming soon

## Summary

That completes the overview.
""")

    result = render_template(root, "ctx:nested-test")

    # Check that all sections are inserted
    assert "def main():" in result
    assert "Project Documentation" in result
    assert "def test_main():" in result

    # Check that document structure is preserved
    assert "1. Main module:" in result
    assert "2. Documentation:" in result
    assert "3. Tests:" in result
    assert "That completes the overview." in result


@pytest.mark.parametrize("section_name,expected_content", [
    ("src", "def main():"),
    ("docs", "Project Documentation"),
    ("tests", "def test_main():"),
    ("all", "def main():")  # all section includes all files
])
def test_section_placeholder_parametrized(basic_project, section_name, expected_content):
    """Parametrized test of various section placeholders."""
    root = basic_project

    template_content = f"""# Param Test

${{{section_name}}}
"""
    create_template(root, f"param-test-{section_name}", template_content)

    result = render_template(root, f"ctx:param-test-{section_name}")
    assert expected_content in result


def test_section_placeholder_with_complex_names(fragments_project):
    """Test placeholders with complex section names."""
    root = fragments_project

    # Test various section name formats
    create_template(root, "complex-names-test", """# Complex Names Test

## Simple name
${main}

## Name with slash
${security/auth}

## Name with dash from fragment
${api/api-v1}
""")

    result = render_template(root, "ctx:complex-names-test")

    assert "print('main')" in result
    assert "def login(): pass" in result
    assert "def handle(): pass" in result


def test_section_placeholder_case_sensitivity(basic_project):
    """Test case sensitivity in section names."""
    root = basic_project

    create_template(root, "case-test", """# Case Test

${src}
""")

    result = render_template(root, "ctx:case-test")
    assert "def main():" in result

    # Check that incorrect case causes error
    create_template(root, "case-error-test", """# Case Error Test

${SRC}
""")

    with pytest.raises(TemplateProcessingError, match=r"Section 'SRC' not found"):
        render_template(root, "ctx:case-error-test")
"""
Tests for basic markdown placeholders.

Checks the main functionality of ${md:...} insertion:
- Simple file insertion
- Automatic .md extension addition
- Paths in subdirectories
- Basic heading processing
"""

from __future__ import annotations

import pytest

from lg.template.processor import TemplateProcessingError
from .conftest import md_project, create_template, render_template


def test_simple_md_placeholder(md_project):
    """Test simple insertion ${md:README}."""
    root = md_project

    # Create template with simple markdown placeholder
    create_template(root, "simple-test", """# Test Template

## Project Documentation

${md:README}

End of template.
""")

    result = render_template(root, "ctx:simple-test")

    # Check that README.md content is inserted
    assert "Main Project" in result
    assert "This is the main project documentation." in result
    assert "## Features" in result
    assert "- Feature A" in result
    assert "End of template." in result
    

def test_md_placeholder_adds_extension_automatically(md_project):
    """Test automatic .md extension addition."""
    root = md_project

    # Both variants should work the same
    create_template(root, "extension-test", """# Extension Test

## With explicit .md
${md:README.md}

## Without extension (should auto-add .md)
${md:README}

## Should be identical
""")

    result = render_template(root, "ctx:extension-test")

    # Content should appear twice
    occurrences = result.count("Main Project")
    assert occurrences == 0 # H1 heading is removed by strip_h1

    occurrences = result.count("This is the main project documentation.")
    assert occurrences == 2


def test_md_placeholder_with_subdirectory(md_project):
    """Test insertion of files from subdirectories."""
    root = md_project

    create_template(root, "subdir-test", """# Subdirectory Test

## User Guide
${md:docs/guide}

## API Reference
${md:docs/api}
""")

    result = render_template(root, "ctx:subdir-test")

    # Check content from docs/guide.md
    assert "User Guide" in result
    assert "This is a comprehensive user guide." in result
    assert "## Installation" in result
    assert "Run the installer." in result

    # Check content from docs/api.md
    assert "API Reference" in result
    assert "API documentation." in result
    assert "## Authentication" in result
    assert "### GET /users" in result


def test_md_placeholder_file_not_found_error(md_project):
    """Test error handling when file is not found."""
    root = md_project

    create_template(root, "notfound-test", """# Not Found Test

${md:nonexistent-file}
""")

    # Should raise error about file not found
    with pytest.raises(TemplateProcessingError, match=r"No markdown files found for `md:nonexistent-file.md` placeholder"):
        render_template(root, "ctx:notfound-test")


def test_md_placeholder_empty_file_handling(md_project):
    """Test handling of empty files - should raise error."""
    root = md_project

    # Create empty file
    from .conftest import write
    write(root / "empty.md", "")

    create_template(root, "empty-test", """# Empty Test

Before empty file.

${md:empty}

After empty file.
""")

    # Empty file should raise error
    with pytest.raises(TemplateProcessingError, match=r"No markdown files found for `md:empty.md` placeholder"):
        render_template(root, "ctx:empty-test")


def test_md_placeholder_with_file_without_h1(md_project):
    """Test insertion of file without H1 heading."""
    root = md_project

    create_template(root, "no-h1-test", """# No H1 Test

## Changelog Section

${md:docs/changelog}
""")

    result = render_template(root, "ctx:no-h1-test")

    # File changelog.md contains no H1, only H2
    assert "## v1.0.0" in result
    assert "- Initial release" in result
    assert "## v0.9.0" in result
    assert "- Beta version" in result


def test_multiple_md_placeholders_in_single_template(md_project):
    """Test multiple markdown placeholders in single template."""
    root = md_project

    create_template(root, "multiple-test", """# Multiple MD Test

## Main Documentation
${md:README}

## User Guide
${md:docs/guide}

## API Documentation
${md:docs/api}

## Changelog
${md:docs/changelog}

## Summary
That's all the documentation!
""")

    result = render_template(root, "ctx:multiple-test")

    # Check that all files are included
    assert "Main Project" not in result  # from README
    assert "This is a comprehensive user guide." in result  # from guide
    assert "API documentation." in result  # from api
    assert "### v1.0.0" in result  # from changelog
    assert "That's all the documentation!" in result


def test_md_placeholder_preserves_markdown_structure(md_project):
    """Test preservation of Markdown structure during insertion."""
    root = md_project

    create_template(root, "structure-test", """# Structure Test

${md:docs/api}
""")

    result = render_template(root, "ctx:structure-test")

    # Check that headings of different levels are preserved
    lines = result.split('\n')

    # Should be H2 from file
    h2_lines = [line for line in lines if line.startswith('## ')]
    assert any("API Reference" in line for line in h2_lines)

    # Should be H3 headings
    h3_lines = [line for line in lines if line.startswith('### ')]
    assert any("Authentication" in line for line in h3_lines)
    assert any("Endpoints" in line for line in h3_lines)

    # Should be H4 headings
    h4_lines = [line for line in lines if line.startswith('#### ')]
    assert any("GET /users" in line for line in h4_lines)


def test_md_placeholder_whitespace_handling(md_project):
    """Test whitespace handling around markdown placeholders."""
    root = md_project

    create_template(root, "whitespace-test", """# Whitespace Test

Before placeholder.
${md:README}
After placeholder.

Indented:
    ${md:docs/changelog}
End.
""")

    result = render_template(root, "ctx:whitespace-test")

    # Check correct insertion without formatting issues
    assert "Before placeholder." in result
    assert "After placeholder." in result
    assert "End." in result

    # Content from files should be present
    assert "Main Project" in result
    assert "## v1.0.0" in result


@pytest.mark.parametrize("filename,expected_content", [
    ("README", "Main Project"),
    ("docs/guide", "User Guide"),
    ("docs/api", "API Reference"),
    ("docs/changelog", "v1.0.0")
])
def test_md_placeholder_parametrized(md_project, filename, expected_content):
    """Parametrized test for different markdown placeholders."""
    root = md_project

    create_template(root, f"param-test-{filename.replace('/', '-')}", f"""# Param Test

${{md:{filename}}}
""")

    result = render_template(root, f"ctx:param-test-{filename.replace('/', '-')}")
    assert expected_content in result
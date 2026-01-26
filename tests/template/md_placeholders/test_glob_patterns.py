"""
Tests for glob patterns in markdown placeholders.

Checks the functionality of bulk file inclusion:
- ${md:docs/*} for including all files in folder
- ${md:docs/**} for recursive inclusion
- Different glob patterns
- Handling of file inclusion order
- Combinations of globs with other parameters
"""

from __future__ import annotations

import pytest

from .conftest import (
    md_project, create_template, render_template, 
    create_glob_test_files, write_markdown
)


def test_glob_basic_directory_wildcard(md_project):
    """Test basic glob for all files in directory."""
    root = md_project

    # Create additional files for testing globs
    create_glob_test_files(root)

    create_template(root, "glob-basic-test", """# Glob Basic Test

## All Documentation Files
${md:docs/*.md}

End of test.
""")

    result = render_template(root, "ctx:glob-basic-test")

    # Check that all files from docs/ are included
    assert "User Guide" in result           # from guide.md (already existed)
    assert "API Reference" in result        # from api.md (already existed)
    assert "Project overview" in result     # from overview.md (new)
    assert "Step by step tutorial" in result  # from tutorial.md (new)
    assert "Frequently asked questions" in result  # from faq.md (new)

    # But files from subdirectories should NOT be included (only *)
    assert "Internal architecture" not in result  # from docs/advanced/internals.md
    assert "Plugin development" not in result     # from docs/advanced/plugins.md

    assert "End of test." in result


def test_glob_recursive_wildcard(md_project):
    """Test recursive glob for all files including subdirectories."""
    root = md_project

    create_glob_test_files(root)

    create_template(root, "glob-recursive-test", """# Recursive Glob Test

## All Documentation (including subdirs)
${md:docs/**}
""")

    result = render_template(root, "ctx:glob-recursive-test")

    # All files should be included, including from subdirectories
    assert "User Guide" in result           # docs/guide.md
    assert "API Reference" in result        # docs/api.md
    assert "Project overview" in result     # docs/overview.md
    assert "Step by step tutorial" in result  # docs/tutorial.md
    assert "Frequently asked questions" in result  # docs/faq.md
    assert "Internal architecture" in result  # docs/advanced/internals.md
    assert "Plugin development" in result     # docs/advanced/plugins.md


def test_glob_specific_pattern(md_project):
    """Test specific glob patterns."""
    root = md_project

    create_glob_test_files(root)

    # Create files with different names for patterns
    write_markdown(root / "docs" / "user-guide.md", "User Guide Extended", "Extended user documentation.")
    write_markdown(root / "docs" / "dev-guide.md", "Developer Guide", "Developer documentation.")
    write_markdown(root / "docs" / "quick-start.md", "Quick Start", "Getting started quickly.")

    create_template(root, "glob-pattern-test", """# Pattern Test

## All *-guide files
${md:docs/*-guide.md}

## All quick-* files
${md:docs/quick-*}
""")

    result = render_template(root, "ctx:glob-pattern-test")

    # Only files matching patterns should be included
    assert "Extended user documentation." in result  # user-guide.md
    assert "Developer documentation." in result      # dev-guide.md
    assert "Getting started quickly." in result      # quick-start.md

    # But other files should not be included
    assert "Project overview" not in result         # overview.md
    assert "Step by step tutorial" not in result    # tutorial.md


def test_glob_with_contextual_analysis(md_project):
    """Test globs with contextual heading analysis."""
    root = md_project

    create_glob_test_files(root)

    create_template(root, "glob-contextual-test", """# Main Documentation

## All Guides Section

### Documentation Files
${md:docs/*}
""")

    result = render_template(root, "ctx:glob-contextual-test")

    # Files should be processed with correct heading levels
    # Under H3 → max_heading_level=4, but for globs strip_h1=false (H1 preserved)
    assert "#### Installation" in result    # was H2 in guide.md, became H4
    assert "#### Authentication" in result  # was H2 in api.md, became H4

    # H1 headings should NOT be removed for globs (strip_h1=false)
    lines = result.split('\n')
    h1_lines = [line for line in lines if line.startswith('#### ') and ('User Guide' in line or 'API Reference' in line)]
    assert len(h1_lines) == 2  # H1 headings preserved and shifted to H4


def test_glob_with_explicit_parameters(md_project):
    """Test globs with explicit parameters."""
    root = md_project

    create_glob_test_files(root)

    create_template(root, "glob-params-test", """# Parameters Test

## Documentation (level 3, keep H1)
${md:docs/*, level:3, strip_h1:false}

## Advanced Documentation (level 5)
${md:docs/advanced/*, level:5}
""")

    result = render_template(root, "ctx:glob-params-test")

    # First glob: level:3, strip_h1:false
    assert "### User Guide" in result       # H1 preserved, became H3
    assert "### API Reference" in result    # H1 preserved, became H3
    assert "#### Installation" in result    # was H2, became H4

    # Second glob: level:5 (strip_h1 default)
    assert "##### Internals" in result      # H1 from internals.md became H5
    assert "##### Plugins" in result        # H1 from plugins.md became H5


def test_glob_with_conditional_inclusion(md_project):
    """Test globs with conditional inclusion."""
    root = md_project

    create_glob_test_files(root)

    create_template(root, "glob-conditional-test", """# Conditional Glob Test

## Basic Docs (always)
${md:docs/*.md}

## Advanced Docs (only if advanced tag)
${md:docs/advanced/*, if:tag:advanced}
""")

    # Without tags - only basic files
    result1 = render_template(root, "ctx:glob-conditional-test")
    assert "User Guide" in result1          # basic file
    assert "Internal architecture" not in result1  # from advanced/

    # With advanced tag - all files
    from .conftest import make_run_options
    options_advanced = make_run_options(extra_tags={"advanced"})
    result2 = render_template(root, "ctx:glob-conditional-test", options_advanced)
    assert "User Guide" in result2          # basic file
    assert "Internal architecture" in result2  # from advanced/


def test_glob_file_ordering(md_project):
    """Test file ordering when using globs."""
    root = md_project

    # Create files with predictable names to check order
    write_markdown(root / "ordered" / "01-first.md", "First Document", "This is the first document.")
    write_markdown(root / "ordered" / "02-second.md", "Second Document", "This is the second document.")
    write_markdown(root / "ordered" / "03-third.md", "Third Document", "This is the third document.")

    create_template(root, "glob-order-test", """# Order Test

${md:ordered/*}
""")

    result = render_template(root, "ctx:glob-order-test")

    # Check that files are in alphabetical order (standard glob behavior)
    first_pos = result.find("This is the first document.")
    second_pos = result.find("This is the second document.")
    third_pos = result.find("This is the third document.")

    assert first_pos < second_pos < third_pos, "Files should be in alphabetical order"


def test_glob_with_anchors_error(md_project):
    """Test that globs don't support anchor links."""
    root = md_project

    create_template(root, "glob-anchor-error-test", """# Glob Anchor Error

${md:docs/*#Authentication}
""")

    # Globs with anchor links should raise error
    with pytest.raises(Exception):  # ValueError about globs and anchors incompatibility
        render_template(root, "ctx:glob-anchor-error-test")


@pytest.mark.parametrize("pattern,expected_files", [
    ("docs/g*", ["guide"]),                    # files starting with 'g'
    ("docs/*guide*", ["guide"]),              # files containing 'guide'
    ("docs/a*", ["api"]),                     # files starting with 'a'
    ("docs/???.md", ["api"]),                 # files of 3 characters + .md
])
def test_glob_patterns_parametrized(md_project, pattern, expected_files):
    """Parametrized test for different glob patterns."""
    root = md_project

    create_template(root, f"glob-param-{pattern.replace('/', '-').replace('*', 'star').replace('?', 'q')}", f"""# Pattern Test

${{md:{pattern}}}
""")

    result = render_template(root, f"ctx:glob-param-{pattern.replace('/', '-').replace('*', 'star').replace('?', 'q')}")

    # Check presence of expected files
    for expected_file in expected_files:
        if expected_file == "guide":
            assert "User Guide" in result
        elif expected_file == "api":
            assert "API Reference" in result
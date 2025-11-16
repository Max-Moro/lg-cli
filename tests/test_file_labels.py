"""
Tests for file labels in rendered content.

Tests:
- Integration of labels in fenced blocks (each file in its own block)
- Different path_labels modes (scope_relative, relative, basename)
- Correctness of labels in different project structures
"""

from pathlib import Path

from tests.infrastructure import (
    write_source_file, write_markdown,
    create_sections_yaml, create_template,
    make_engine
)


class TestFileLabelIntegration:
    """Tests for integration of file labels in rendered content."""

    def test_python_files_have_individual_fence_blocks_with_labels(self, tmp_path: Path):
        """Each Python file should be in its own fenced block with a label."""
        root = tmp_path

        # Create Python files
        write_source_file(root / "src" / "alpha.py", "def alpha(): pass")
        write_source_file(root / "src" / "beta.py", "def beta(): pass")

        # Section configuration
        create_sections_yaml(root, {
            "python-src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })

        # Context
        create_template(root, "test", "${python-src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check: two separate fenced blocks with labels
        assert "```python:src/alpha.py" in result
        assert "```python:src/beta.py" in result

        # Check that each file is in its own block (closing ```)
        assert result.count("```python:") == 2
        assert result.count("```\n") >= 2  # at least 2 closing blocks

    def test_markdown_files_no_fence_blocks(self, tmp_path: Path):
        """Markdown files without fenced blocks only when ALL files are markdown."""
        root = tmp_path

        # Create ONLY Markdown files
        write_markdown(root / "docs" / "intro.md", "Introduction", "Some intro text")
        write_markdown(root / "docs" / "guide.md", "Guide", "Some guide text")

        # Section configuration (ONLY .md)
        create_sections_yaml(root, {
            "docs": {
                "extensions": [".md"],
                "markdown": {"max_heading_level": 2},
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/docs/**"]
                }
            }
        })

        # Context
        create_template(root, "test", "${docs}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check: NO fenced blocks for markdown
        assert "```markdown" not in result
        assert "```" not in result

        # Content is present directly (order: alphabetical)
        assert "## Guide" in result
        assert "Some guide text" in result
        assert "## Introduction" in result
        assert "Some intro text" in result

        # Check order (guide comes before intro - alphabetical)
        guide_pos = result.find("## Guide")
        intro_pos = result.find("## Introduction")
        assert guide_pos < intro_pos


class TestPathLabelsMode:
    """Tests for different label display modes."""

    def test_path_labels_relative(self, tmp_path: Path):
        """Mode 'relative': full path relative to repo root."""
        root = tmp_path

        # Create files in different folders
        write_source_file(root / "pkg" / "core" / "engine.py", "# Engine")
        write_source_file(root / "pkg" / "utils" / "helpers.py", "# Helpers")

        # Configuration
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })

        create_template(root, "test", "${src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check full relative paths
        assert "```python:pkg/core/engine.py" in result
        assert "```python:pkg/utils/helpers.py" in result

    def test_path_labels_basename(self, tmp_path: Path):
        """Mode 'basename': minimal unique suffix."""
        root = tmp_path

        # Create files with same names in different folders
        write_source_file(root / "pkg" / "a" / "utils.py", "# Utils A")
        write_source_file(root / "pkg" / "b" / "utils.py", "# Utils B")
        write_source_file(root / "pkg" / "unique.py", "# Unique")

        # Configuration
        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })

        create_template(root, "test", "${src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check: for utils.py - minimal unique suffixes (one directory)
        assert "```python:a/utils.py" in result
        assert "```python:b/utils.py" in result

        # For unique file - basename only
        assert "```python:unique.py" in result

    def test_path_labels_scope_relative(self, tmp_path: Path):
        """Mode 'scope_relative': relative to scope_dir (for local sections)."""
        root = tmp_path

        # Create files
        write_source_file(root / "app" / "web" / "server.py", "# Server")
        write_source_file(root / "app" / "web" / "routes.py", "# Routes")

        # Configuration in root lg-cfg
        create_sections_yaml(root, {
            "web-src": {
                "extensions": [".py"],
                "path_labels": "scope_relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/app/web/**"]
                }
            }
        })

        create_template(root, "test", "${web-src}", template_type="ctx")

        # Render from root (origin = "self")
        engine = make_engine(root)
        result = engine.render_context("test")

        # For root scope scope_relative is equivalent to relative
        assert "```python:app/web/server.py" in result
        assert "```python:app/web/routes.py" in result


class TestComplexProjectStructure:
    """Tests for complex project structures."""

    def test_deep_nested_structure_with_basename(self, tmp_path: Path):
        """Deep nesting with basename mode."""
        root = tmp_path

        # Create deeply nested structure
        write_source_file(root / "pkg" / "core" / "engine" / "runtime.py", "# Runtime")
        write_source_file(root / "pkg" / "plugins" / "loader" / "runtime.py", "# Plugin Runtime")
        write_source_file(root / "pkg" / "utils" / "helpers.py", "# Helpers")

        # Configuration
        create_sections_yaml(root, {
            "all-src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/pkg/**"]
                }
            }
        })

        create_template(root, "test", "${all-src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check minimal unique suffixes for runtime.py
        # Should differ by folder
        lines = result.split("\n")
        runtime_labels = [line for line in lines if "runtime.py" in line and line.startswith("```python:")]

        assert len(runtime_labels) == 2
        # Labels should be different
        assert runtime_labels[0] != runtime_labels[1]

        # helpers.py should have minimal suffix
        assert "```python:helpers.py" in result

    def test_mixed_languages_separate_fence_blocks(self, tmp_path: Path):
        """Mixed languages: each file in its own block with its own language."""
        root = tmp_path

        # Create files of different languages
        write_source_file(root / "src" / "app.py", "# Python app", language="python")
        write_source_file(root / "src" / "types.ts", "// TypeScript types", language="typescript")
        write_markdown(root / "src" / "README.md", "Readme", "Documentation")

        # Configuration for all types
        create_sections_yaml(root, {
            "all-src": {
                "extensions": [".py", ".ts", ".md"],
                "path_labels": "relative",
                "markdown": {"max_heading_level": 2},
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })

        create_template(root, "test", "${all-src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # IMPORTANT: Markdown also in fence block (all files in individual blocks)
        assert "```markdown:src/README.md" in result
        assert "```python:src/app.py" in result
        assert "```typescript:src/types.ts" in result

        # Check content presence
        assert "Documentation" in result
        assert "## Readme" in result


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_file_section(self, tmp_path: Path):
        """Section with a single file."""
        root = tmp_path

        write_source_file(root / "main.py", "# Main application")

        create_sections_yaml(root, {
            "main": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/main.py"]
                }
            }
        })

        create_template(root, "test", "${main}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check for single block
        assert result.count("```python:") == 1
        assert "```python:main.py" in result

    def test_empty_section_no_labels(self, tmp_path: Path):
        """Empty section (no files) - no labels."""
        root = tmp_path

        # Create section, but files don't match filters
        write_source_file(root / "other" / "file.py", "# Other")

        create_sections_yaml(root, {
            "empty": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/nonexistent/**"]
                }
            }
        })

        create_template(root, "test", "${empty}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check: no fenced blocks
        assert "```python:" not in result
        # Result should be empty or almost empty
        assert result.strip() == "" or len(result.strip()) < 10

    def test_files_with_same_basename_different_paths(self, tmp_path: Path):
        """Files with same basename in different paths."""
        root = tmp_path

        # Create many files with same name
        write_source_file(root / "a" / "b" / "c" / "utils.py", "# ABC Utils")
        write_source_file(root / "a" / "b" / "utils.py", "# AB Utils")
        write_source_file(root / "a" / "utils.py", "# A Utils")
        write_source_file(root / "utils.py", "# Root Utils")

        create_sections_yaml(root, {
            "all": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/**"]
                }
            }
        })

        create_template(root, "test", "${all}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # All 4 files should be in result
        assert result.count("```python:") == 4

        # Labels should be unique
        lines = result.split("\n")
        labels = [line.strip() for line in lines if line.strip().startswith("```python:")]

        assert len(labels) == 4
        assert len(set(labels)) == 4  # All unique


class TestLabelConsistency:
    """Tests for label consistency."""

    def test_labels_consistent_across_multiple_renders(self, tmp_path: Path):
        """Labels remain stable on re-rendering."""
        root = tmp_path

        # Create files
        write_source_file(root / "src" / "a.py", "# A")
        write_source_file(root / "src" / "b.py", "# B")
        write_source_file(root / "src" / "c.py", "# C")

        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "basename",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })

        create_template(root, "test", "${src}", template_type="ctx")

        # Render twice
        engine1 = make_engine(root)
        result1 = engine1.render_context("test")

        engine2 = make_engine(root)
        result2 = engine2.render_context("test")

        # Results should be identical
        assert result1 == result2

    def test_labels_stable_with_file_order_change(self, tmp_path: Path):
        """Labels are stable regardless of file order in FS."""
        root = tmp_path

        # Create files (order may vary in FS)
        files = [
            root / "src" / "zebra.py",
            root / "src" / "alpha.py",
            root / "src" / "delta.py",
        ]

        for f in files:
            write_source_file(f, f"# {f.stem}")

        create_sections_yaml(root, {
            "src": {
                "extensions": [".py"],
                "path_labels": "relative",
                "filters": {
                    "mode": "allow",
                    "allow": ["/src/**"]
                }
            }
        })

        create_template(root, "test", "${src}", template_type="ctx")

        # Render
        engine = make_engine(root)
        result = engine.render_context("test")

        # Check that all files are present (order is alphabetical thanks to sorting)
        assert "```python:src/alpha.py" in result
        assert "```python:src/delta.py" in result
        assert "```python:src/zebra.py" in result

        # Check order (should be alphabetical)
        alpha_pos = result.find("```python:src/alpha.py")
        delta_pos = result.find("```python:src/delta.py")
        zebra_pos = result.find("```python:src/zebra.py")

        assert alpha_pos < delta_pos < zebra_pos

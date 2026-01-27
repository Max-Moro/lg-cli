"""
Tests for context resolution: section collection, frontmatter, meta-sections.

Covers ТЗ §11.2 (meta-section render error), §11.3 (frontmatter),
§11.4 (transitive section collection), §11.5 (single integration mode-set rule).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.infrastructure import (
    write, render_template, run_cli,
    create_mode_meta_section, create_tag_meta_section,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig,
)


class TestMetaSections:
    """Tests for meta-section behavior."""

    def test_render_meta_section_raises_error(self, tmp_path, monkeypatch):
        """Rendering a meta-section (no filters) must produce an error."""
        root = tmp_path
        monkeypatch.chdir(root)

        # Create meta-section (no filters)
        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        # Regular section so sections.yaml exists
        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "main.py", "x = 1\n")

        # Try to render the meta-section via CLI
        result = run_cli(root, "render", "sec:ai-interaction")
        assert result.returncode != 0


class TestFrontmatter:
    """Tests for frontmatter include and stripping."""

    def test_frontmatter_includes_meta_sections_in_model(self, tmp_path):
        """Frontmatter include adds meta-sections to adaptive model."""
        root = tmp_path

        # Integration mode-set
        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        # Tag-set meta-section (only accessible via frontmatter include)
        create_tag_meta_section(root, "my-tags", {
            "language": TagSetConfig(
                title="Languages",
                tags={"python": TagConfig(title="Python")}
            )
        })

        # Section extends only ai-interaction (not my-tags)
        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-interaction"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        # Context frontmatter includes my-tags (adds tag-sets to model)
        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-interaction", "my-tags"]
        ---
        # Test
        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_tag_sets
        result = list_tag_sets(root, "test")
        tag_set_ids = {ts.id for ts in result.tag_sets}

        assert "language" in tag_set_ids

    def test_frontmatter_stripped_from_render(self, tmp_path):
        """Frontmatter should not appear in rendered output."""
        root = tmp_path

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-interaction"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-interaction"]
        ---
        # Rendered Content
        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        rendered = render_template(root, "ctx:test")

        assert "include:" not in rendered
        assert "Rendered Content" in rendered


class TestSectionCollection:
    """Tests for transitive section collection from templates."""

    def test_sections_from_template_includes_collected(self, tmp_path):
        """Sections used in nested tpl includes should contribute to adaptive model."""
        root = tmp_path

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        # Tag-set meta-section used only by docs section
        create_tag_meta_section(root, "extra-tags", {
            "extra": TagSetConfig(
                title="Extra",
                tags={"special": TagConfig(title="Special")}
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-interaction"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/src/**"

        docs:
          extends: ["ai-interaction", "extra-tags"]
          extensions: [".md"]
          filters:
            mode: allow
            allow:
              - "/docs/**"
        """))

        # Template includes docs section
        write(root / "lg-cfg" / "inner.tpl.md", "## Inner\n${docs}\n")

        # Context includes template (transitive) and src section
        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-interaction"]
        ---
        # Test
        ${tpl:inner}
        ${src}
        """))

        write(root / "src" / "main.py", "x = 1\n")
        write(root / "docs" / "README.md", "# Docs\n")

        from lg.adaptive.listing import list_tag_sets
        result = list_tag_sets(root, "test")
        tag_set_ids = {ts.id for ts in result.tag_sets}

        # extra-tags from docs section (through tpl:inner) should be present
        assert "extra" in tag_set_ids

    def test_sections_in_conditional_blocks_collected(self, tmp_path):
        """Sections inside {% if %} blocks should be collected regardless of condition value."""
        root = tmp_path

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        create_tag_meta_section(root, "cond-tags", {
            "conditional": TagSetConfig(
                title="Conditional",
                tags={"cond-tag": TagConfig(title="Conditional Tag")}
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-interaction"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/src/**"

        extras:
          extends: ["ai-interaction", "cond-tags"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/extras/**"
        """))

        # Context with section inside conditional block (condition is never true)
        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-interaction"]
        ---
        # Test
        ${src}
        {% if tag:never_active_tag %}
        ${extras}
        {% endif %}
        """))

        write(root / "src" / "main.py", "x = 1\n")
        write(root / "extras" / "extra.py", "y = 2\n")

        from lg.adaptive.listing import list_tag_sets
        result = list_tag_sets(root, "test")
        tag_set_ids = {ts.id for ts in result.tag_sets}

        # Tag-set from extras should still be collected (conditions not evaluated)
        assert "conditional" in tag_set_ids


class TestIntegrationModeSetRule:
    """Tests for the single integration mode-set rule."""

    def test_exactly_one_integration_modeset_ok(self, tmp_path):
        """Context with exactly one integration mode-set should succeed."""
        root = tmp_path

        # One integration mode-set (has runs)
        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        # One content mode-set (no runs)
        create_mode_meta_section(root, "content-modes", {
            "content": ModeSetConfig(
                title="Content",
                modes={
                    "full": ModeConfig(title="Full"),
                    "minimal": ModeConfig(title="Minimal", tags=["minimal"]),
                }
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-interaction", "content-modes"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-interaction", "content-modes"]
        ---
        # Test
        ${src}
        """))
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_mode_sets
        result = list_mode_sets(root, "test", "com.test.provider")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        content_set = next(ms for ms in result.mode_sets if ms.id == "content")

        assert ai_set.integration is True
        assert content_set.integration is False

    def test_multiple_integration_modesets_error(self, tmp_path):
        """Context with >1 integration mode-sets should raise error."""
        root = tmp_path

        # First integration mode-set
        create_mode_meta_section(root, "modes-1", {
            "integration-1": ModeSetConfig(
                title="Integration 1",
                modes={
                    "m1": ModeConfig(title="M1", runs={"com.test.provider": "--m1"}),
                }
            )
        })

        # Second integration mode-set
        create_mode_meta_section(root, "modes-2", {
            "integration-2": ModeSetConfig(
                title="Integration 2",
                modes={
                    "m2": ModeConfig(title="M2", runs={"com.other.provider": "--m2"}),
                }
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["modes-1", "modes-2"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["modes-1", "modes-2"]
        ---
        # Test
        ${src}
        """))
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.errors import MultipleIntegrationModeSetsError
        from lg.adaptive.listing import list_mode_sets

        with pytest.raises(MultipleIntegrationModeSetsError):
            list_mode_sets(root, "test", "com.test.provider")

    def test_zero_integration_modesets_error(self, tmp_path):
        """Context with 0 integration mode-sets should raise error."""
        root = tmp_path

        # Only content mode-set (no runs)
        create_mode_meta_section(root, "content-only", {
            "content": ModeSetConfig(
                title="Content",
                modes={
                    "full": ModeConfig(title="Full"),
                }
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["content-only"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
        ---
        include: ["content-only"]
        ---
        # Test
        ${src}
        """))
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.errors import NoIntegrationModeSetError
        from lg.adaptive.listing import list_mode_sets

        with pytest.raises(NoIntegrationModeSetError):
            list_mode_sets(root, "test", "com.test.provider")

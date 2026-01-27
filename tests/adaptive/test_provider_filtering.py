"""
Tests for provider filtering, clipboard universal provider, and normalization.

Covers ТЗ §11.6 (provider filtering + empty error),
§11.8 (provider: condition normalization).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.infrastructure import (
    write, render_template, run_cli,
    create_mode_meta_section,
    ModeConfig, ModeSetConfig,
)


class TestProviderFiltering:
    """Tests for provider-based mode-set filtering."""

    def test_integration_modeset_filtered_by_provider(self, multi_provider_project):
        """Integration mode-set should only contain modes supporting the given provider."""
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        # com.partial.provider.cli only supports "ask"
        result = list_mode_sets(root, "test", "com.partial.provider.cli")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        mode_ids = {m.id for m in ai_set.modes}

        assert "ask" in mode_ids
        assert "agent" not in mode_ids
        assert "plan" not in mode_ids

    def test_all_modes_returned_for_full_provider(self, multi_provider_project):
        """Provider supporting all modes should see all of them."""
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        # com.test.provider.cli supports ask, agent, plan
        result = list_mode_sets(root, "test", "com.test.provider.cli")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        mode_ids = {m.id for m in ai_set.modes}

        assert "ask" in mode_ids
        assert "agent" in mode_ids
        assert "plan" in mode_ids

    def test_content_modeset_not_filtered(self, multi_provider_project):
        """Content mode-sets should be returned in full, regardless of provider."""
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        # Even with partial provider, content mode-set is full
        result = list_mode_sets(root, "test", "com.partial.provider.cli")

        dev_set = next(ms for ms in result.mode_sets if ms.id == "dev-stage")
        mode_ids = {m.id for m in dev_set.modes}

        assert "development" in mode_ids
        assert "review" in mode_ids

    def test_unsupported_provider_raises_error(self, multi_provider_project):
        """Provider with no matching modes should raise ProviderNotSupportedError."""
        from lg.adaptive.errors import ProviderNotSupportedError
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        with pytest.raises(ProviderNotSupportedError):
            list_mode_sets(root, "test", "com.unknown.provider")

    def test_integration_flag_on_modesets(self, multi_provider_project):
        """Integration mode-sets should have integration=True, content=False."""
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        result = list_mode_sets(root, "test", "com.test.provider.cli")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        dev_set = next(ms for ms in result.mode_sets if ms.id == "dev-stage")

        assert ai_set.integration is True
        assert dev_set.integration is False


class TestClipboardProvider:
    """Tests for clipboard as universal provider."""

    def test_clipboard_returns_all_modes(self, multi_provider_project):
        """Clipboard provider should return all modes from integration mode-set."""
        from lg.adaptive.listing import list_mode_sets

        root = multi_provider_project

        result = list_mode_sets(root, "test", "clipboard")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        mode_ids = {m.id for m in ai_set.modes}

        assert "ask" in mode_ids
        assert "agent" in mode_ids
        assert "plan" in mode_ids

    def test_clipboard_contexts_returns_all(self, multi_provider_project):
        """list_contexts_for_provider with clipboard should return all contexts."""
        from lg.adaptive.listing import list_contexts_for_provider

        root = multi_provider_project

        all_contexts = list_contexts_for_provider(root, "clipboard")
        assert "test" in all_contexts

    def test_list_contexts_filters_incompatible(self, tmp_path):
        """list_contexts_for_provider should exclude contexts without matching provider."""
        root = tmp_path

        # Context supporting only provider-a
        create_mode_meta_section(root, "modes-a", {
            "ai": ModeSetConfig(
                title="AI",
                modes={"m": ModeConfig(title="M", runs={"provider-a": "--a"})}
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["modes-a"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "ctx-a.ctx.md", textwrap.dedent("""\
        ---
        include: ["modes-a"]
        ---
        # A
        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_contexts_for_provider

        # provider-a should find ctx-a
        contexts_a = list_contexts_for_provider(root, "provider-a")
        assert "ctx-a" in contexts_a

        # provider-b should not find ctx-a
        contexts_b = list_contexts_for_provider(root, "provider-b")
        assert "ctx-a" not in contexts_b


class TestProviderNormalization:
    """Tests for provider ID normalization."""

    @pytest.mark.parametrize("full_id,expected_base", [
        ("com.anthropic.claude.cli", "com.anthropic.claude"),
        ("com.github.copilot.ext", "com.github.copilot"),
        ("com.openai.codex.api", "com.openai.codex"),
        ("clipboard", "clipboard"),
        ("com.jetbrains.ai", "com.jetbrains.ai"),
    ])
    def test_normalize_provider_id(self, full_id, expected_base):
        """Provider IDs should be normalized by stripping technical suffixes."""
        from lg.run_context import normalize_provider_id

        assert normalize_provider_id(full_id) == expected_base

    def test_provider_condition_matches_normalized_id(self, tmp_path):
        """provider:<base-id> condition should match against normalized provider."""
        root = tmp_path

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI",
                modes={
                    "ask": ModeConfig(
                        title="Ask",
                        runs={"com.anthropic.claude.cli": "--ask"},
                    ),
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
        # Test

        {% if provider:com.anthropic.claude %}
        ## Claude Provider Active
        {% endif %}

        {% if provider:com.github.copilot %}
        ## Copilot Provider Active
        {% endif %}

        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        from lg.types import RunOptions
        options = RunOptions(provider="com.anthropic.claude.cli")

        rendered = render_template(root, "ctx:test", options)

        assert "Claude Provider Active" in rendered
        assert "Copilot Provider Active" not in rendered

    def test_provider_condition_false_when_not_specified(self, tmp_path):
        """provider: condition should be False when --provider is not specified."""
        root = tmp_path

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI",
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
        # Test

        {% if provider:com.test.provider %}
        ## Provider Active
        {% else %}
        ## No Provider
        {% endif %}

        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        # No provider specified
        rendered = render_template(root, "ctx:test")

        assert "Provider Active" not in rendered
        assert "No Provider" in rendered

    def test_provider_flag_via_cli(self, tmp_path, monkeypatch):
        """--provider flag should propagate through CLI to template conditions."""
        root = tmp_path
        monkeypatch.chdir(root)

        create_mode_meta_section(root, "ai-interaction", {
            "ai-interaction": ModeSetConfig(
                title="AI",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider.cli": "--ask"}),
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
        # Test

        {% if provider:com.test.provider %}
        ## Provider Active
        {% else %}
        ## No Provider
        {% endif %}

        ${src}
        """))

        write(root / "main.py", "x = 1\n")

        # CLI with --provider
        result = run_cli(root, "render", "ctx:test",
                         "--provider", "com.test.provider.cli")
        assert result.returncode == 0
        assert "Provider Active" in result.stdout
        assert "No Provider" not in result.stdout

        # CLI without --provider
        result2 = run_cli(root, "render", "ctx:test")
        assert result2.returncode == 0
        assert "No Provider" in result2.stdout

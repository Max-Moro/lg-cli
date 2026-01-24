"""
Tests for CLI interface of adaptive features.

Tests the list mode-sets, list tag-sets commands and usage of
--mode and --tags flags through CLI interface.
"""

from __future__ import annotations

from tests.infrastructure import run_cli, jload
from .conftest import adaptive_project, federated_project


def test_list_mode_sets_cli(adaptive_project, monkeypatch):
    """Test list mode-sets command."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    # First create a context to query
    write(root / "lg-cfg" / "list-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# List Test
${src}
""")

    result = run_cli(root, "list", "mode-sets",
                     "--context", "list-test",
                     "--provider", "com.test.provider")

    assert result.returncode == 0
    data = jload(result.stdout)

    # Check response structure
    assert "mode-sets" in data
    mode_sets = data["mode-sets"]

    # Check presence of expected mode sets
    mode_set_ids = {ms["id"] for ms in mode_sets}
    assert "ai-interaction" in mode_set_ids
    assert "dev-stage" in mode_set_ids

    # Check structure of one set
    ai_set = next(ms for ms in mode_sets if ms["id"] == "ai-interaction")
    assert ai_set["title"] == "AI Interaction"
    assert "modes" in ai_set

    # Check modes inside the set
    modes = {m["id"]: m for m in ai_set["modes"]}
    assert "ask" in modes
    assert "agent" in modes

    agent_mode = modes["agent"]
    assert agent_mode["title"] == "Agent work"
    assert "tags" in agent_mode
    assert "agent" in agent_mode["tags"]
    assert "tools" in agent_mode["tags"]


def test_list_tag_sets_cli(adaptive_project, monkeypatch):
    """Test list tag-sets command."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    # Create context for query
    write(root / "lg-cfg" / "tags-list-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Tags List Test
${src}
""")

    result = run_cli(root, "list", "tag-sets", "--context", "tags-list-test")

    assert result.returncode == 0
    data = jload(result.stdout)

    # Check response structure
    assert "tag-sets" in data
    tag_sets = data["tag-sets"]

    # Check presence of expected tag sets
    tag_set_ids = {ts["id"] for ts in tag_sets}
    assert "language" in tag_set_ids
    assert "code-type" in tag_set_ids

    # Check global tags
    global_set = next((ts for ts in tag_sets if ts["id"] == "global"), None)
    if global_set:
        global_tags = {t["id"] for t in global_set["tags"]}
        assert "agent" in global_tags
        assert "review" in global_tags
        assert "minimal" in global_tags


def test_render_with_mode_flags(adaptive_project, monkeypatch):
    """Test rendering with --mode flags."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    # Create a simple context for testing
    write(root / "lg-cfg" / "mode-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Mode Test

{% if tag:agent %}
## Agent Mode Active
{% endif %}

{% if tag:tests %}
## Test Mode Active
{% endif %}

## Content
${src}
""")

    # Test without modes
    result1 = run_cli(root, "render", "ctx:mode-test")
    assert result1.returncode == 0
    assert "Agent Mode Active" not in result1.stdout
    assert "Test Mode Active" not in result1.stdout
    assert "Content" in result1.stdout

    # Test with one mode
    result2 = run_cli(root, "render", "ctx:mode-test", "--mode", "ai-interaction:agent")
    assert result2.returncode == 0
    assert "Agent Mode Active" in result2.stdout
    assert "Test Mode Active" not in result2.stdout

    # Test with multiple modes
    result3 = run_cli(root, "render", "ctx:mode-test",
                      "--mode", "ai-interaction:agent",
                      "--mode", "dev-stage:testing")
    assert result3.returncode == 0
    assert "Agent Mode Active" in result3.stdout
    assert "Test Mode Active" in result3.stdout


def test_render_with_tags_flags(adaptive_project, monkeypatch):
    """Test rendering with --tags flag."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    # Create context for testing tags
    write(root / "lg-cfg" / "tags-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Tags Test

{% if tag:minimal %}
## Minimal Version
{% endif %}

{% if tag:python %}
## Python Content
{% endif %}

{% if tag:review %}
## Review Mode
{% endif %}

## Base Content
${docs}
""")

    # Test without additional tags
    result1 = run_cli(root, "render", "ctx:tags-test")
    assert result1.returncode == 0
    assert "Minimal Version" not in result1.stdout
    assert "Python Content" not in result1.stdout

    # Test with one tag
    result2 = run_cli(root, "render", "ctx:tags-test", "--tags", "minimal")
    assert result2.returncode == 0
    assert "Minimal Version" in result2.stdout
    assert "Python Content" not in result2.stdout

    # Test with multiple tags
    result3 = run_cli(root, "render", "ctx:tags-test", "--tags", "minimal,python,review")
    assert result3.returncode == 0
    assert "Minimal Version" in result3.stdout
    assert "Python Content" in result3.stdout
    assert "Review Mode" in result3.stdout


def test_combined_modes_and_tags_cli(adaptive_project, monkeypatch):
    """Test combined use of --mode and --tags."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    write(root / "lg-cfg" / "combined-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Combined Test

{% if tag:agent %}
## Agent from Mode
{% endif %}

{% if tag:tools %}
## Tools from Mode
{% endif %}

{% if tag:custom %}
## Custom from Tags
{% endif %}

${src}
""")

    # Combine mode (which activates agent, tools) with additional tag
    result = run_cli(root, "render", "ctx:combined-test",
                     "--mode", "ai-interaction:agent",
                     "--tags", "custom")

    assert result.returncode == 0
    # Tags from mode should be activated
    assert "Agent from Mode" in result.stdout
    assert "Tools from Mode" in result.stdout
    # Additional tag should also work
    assert "Custom from Tags" in result.stdout


def test_report_with_adaptive_options(adaptive_project, monkeypatch):
    """Test report command with adaptive options."""
    root = adaptive_project
    monkeypatch.chdir(root)

    result = run_cli(root, "report", "sec:src",
                     "--mode", "ai-interaction:agent",
                     "--tags", "python")

    assert result.returncode == 0
    data = jload(result.stdout)

    # Check basic report structure
    assert "protocol" in data
    assert "target" in data
    assert "total" in data
    assert "files" in data

    # Check that report contains files
    assert len(data["files"]) > 0

    # Check metadata
    assert data["target"] == "sec:src"
    assert data["scope"] == "section"


def test_invalid_mode_cli_error(adaptive_project, monkeypatch):
    """Test error handling for invalid mode via CLI."""
    root = adaptive_project
    monkeypatch.chdir(root)

    # Invalid mode set
    result1 = run_cli(root, "render", "sec:src", "--mode", "invalid:mode")
    assert result1.returncode == 2
    assert "Unknown mode set 'invalid'" in result1.stderr

    # Invalid mode in correct set
    result2 = run_cli(root, "render", "sec:src", "--mode", "ai-interaction:invalid")
    assert result2.returncode == 2
    assert "Unknown mode 'invalid' in mode set 'ai-interaction'" in result2.stderr


def test_invalid_mode_format_cli_error(adaptive_project, monkeypatch):
    """Test error handling for invalid mode format."""
    root = adaptive_project
    monkeypatch.chdir(root)

    # Invalid format (without colon)
    result = run_cli(root, "render", "sec:src", "--mode", "invalid-format")
    assert result.returncode == 2
    assert "Invalid mode format" in result.stderr


def test_federated_modes_cli(federated_project, monkeypatch):
    """Test CLI commands with federated structure."""
    from tests.infrastructure.file_utils import write

    root = federated_project
    monkeypatch.chdir(root)

    # Create context in federated project
    write(root / "lg-cfg" / "fed-modes-test.ctx.md", """---
include: ["ai-interaction", "workflow"]
---
# Federated Modes Test
${overview}
""")

    # Check list mode-sets in federated project
    result = run_cli(root, "list", "mode-sets",
                     "--context", "fed-modes-test",
                     "--provider", "com.test.provider")
    assert result.returncode == 0

    data = jload(result.stdout)
    mode_set_ids = {ms["id"] for ms in data["mode-sets"]}

    # Modes from root scope should be present
    assert "ai-interaction" in mode_set_ids  # integration
    assert "workflow" in mode_set_ids        # content


def test_federated_rendering_cli(federated_project, monkeypatch):
    """Test rendering with modes from child scopes via CLI."""
    from tests.infrastructure.file_utils import write

    root = federated_project
    monkeypatch.chdir(root)

    # Create test context that includes child-scope sections
    # The child sections (web-src, core-lib) extend their scope's mode meta-sections
    write(root / "lg-cfg" / "fed-test.ctx.md", """---
include: ["ai-interaction", "workflow"]
---
# Federated Test

{% if tag:typescript %}
## TypeScript Mode
{% endif %}

{% if tag:python %}
## Python Mode
{% endif %}

## Overview
${overview}

## Web Frontend
${@apps/web:web-src}

## Core Library
${@libs/core:core-lib}
""")

    # Activate mode from child scope
    result = run_cli(root, "render", "ctx:fed-test", "--mode", "frontend:ui")
    assert result.returncode == 0
    assert "TypeScript Mode" in result.stdout
    assert "Python Mode" not in result.stdout

    # Activate mode from another child scope
    result2 = run_cli(root, "render", "ctx:fed-test", "--mode", "library:internals")
    assert result2.returncode == 0
    assert "Python Mode" in result2.stdout
    assert "TypeScript Mode" not in result2.stdout


def test_empty_tags_parameter(adaptive_project, monkeypatch):
    """Test empty --tags parameter."""
    root = adaptive_project
    monkeypatch.chdir(root)

    # Empty tag string should work like no tags
    result = run_cli(root, "render", "sec:src", "--tags", "")
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_whitespace_in_tags_parameter(adaptive_project, monkeypatch):
    """Test handling of whitespace in --tags parameter."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    write(root / "lg-cfg" / "whitespace-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Whitespace Test

{% if tag:minimal %}
## Minimal Active
{% endif %}

{% if tag:python %}
## Python Active
{% endif %}
""")

    # Test whitespace around tags
    result = run_cli(root, "render", "ctx:whitespace-test", "--tags", " minimal , python ")
    assert result.returncode == 0
    assert "Minimal Active" in result.stdout
    assert "Python Active" in result.stdout


def test_multiple_mode_parameters(adaptive_project, monkeypatch):
    """Test multiple --mode parameters."""
    from tests.infrastructure.file_utils import write

    root = adaptive_project
    monkeypatch.chdir(root)

    write(root / "lg-cfg" / "multi-mode-test.ctx.md", """---
include: ["ai-interaction", "dev-stage", "tags"]
---
# Multi Mode Test

{% if tag:agent %}
## Agent: Active
{% endif %}

{% if tag:tests %}
## Tests: Active
{% endif %}

{% if tag:review %}
## Review: Active
{% endif %}
""")

    # Use multiple --mode flags
    result = run_cli(root, "render", "ctx:multi-mode-test",
                     "--mode", "ai-interaction:agent",
                     "--mode", "dev-stage:testing")

    assert result.returncode == 0
    assert "Agent: Active" in result.stdout
    assert "Tests: Active" in result.stdout
    assert "Review: Active" not in result.stdout
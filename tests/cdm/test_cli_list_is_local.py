from __future__ import annotations

from pathlib import Path

from tests.infrastructure import run_cli, jload


def test_list_commands_are_local_to_self(monorepo: Path):
    """
    list contexts/sections should only look at @self (root lg-cfg),
    not pick up child-scopes.
    """
    # contexts
    cp = run_cli(monorepo, "list", "contexts")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    # At root we only have 'a' and `x`
    assert data["contexts"] == ["a", "x"]

    # sections
    cp = run_cli(monorepo, "list", "sections")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    # In root sections.yaml: 'root-md' (ai-interaction meta-section is excluded from listing)
    assert data["sections"] == ["root-md"]

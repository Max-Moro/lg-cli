from __future__ import annotations

from pathlib import Path

from tests.conftest import run_cli, jload


def test_list_commands_are_local_to_self(monorepo: Path):
    """
    list contexts/sections должны смотреть только на @self (корневой lg-cfg),
    не поднимать child'ов.
    """
    # contexts
    cp = run_cli(monorepo, "list", "contexts")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    # В корне у нас только 'a' и `x`
    assert data["contexts"] == ["a", "x"]

    # sections
    cp = run_cli(monorepo, "list", "sections")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    # В корневом sections.yaml у фикстуры только 'root-md'
    assert data["sections"] == ["root-md"]

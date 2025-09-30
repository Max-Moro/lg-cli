import textwrap
from pathlib import Path

import pytest

from tests.infrastructure import write


@pytest.fixture
def tmpproj(tmp_path: Path):
    """Минимальный проект под схему: lg-cfg/sections.yaml + ctx/tpl в корне lg-cfg/."""
    root = tmp_path
    # sections.yaml с двумя секциями
    write(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent("""
        all:
          extensions: [".md", ".py"]
          code_fence: true
          markdown:
            max_heading_level: 2
          targets:
            - match: "/pkg/**.py"
              python:
                strip_function_bodies: true
        docs:
          extensions: [".md"]
          code_fence: false
          markdown:
            max_heading_level: 3
          targets:
            - match: ["/docs/**.md"]
        """).strip() + "\n",
    )
    # шаблон и два контекста
    write(root / "lg-cfg" / "a.tpl.md", "Intro\n\n${docs}\n")
    write(root / "lg-cfg" / "a.ctx.md", "Intro (ctx)\n\n${docs}\n")
    write(root / "lg-cfg" / "b.ctx.md", "X ${tpl:a} Y ${all}\n")
    return root

@pytest.fixture(autouse=True)
def _allow_migrations_without_git(monkeypatch):
    # безопасно для юнит-тестов: в проде переменная не задана
    monkeypatch.setenv("LG_MIGRATE_ALLOW_NO_GIT", "1")
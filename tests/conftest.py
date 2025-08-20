import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


def write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p

@pytest.fixture
def tmpproj(tmp_path: Path):
    """Минимальный проект с lg-cfg/config.yaml и папкой contexts/."""
    root = tmp_path
    # config с двумя секциями
    write(
        root / "lg-cfg" / "config.yaml",
        textwrap.dedent("""
        schema_version: 7
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
              markdown:
                drop_paragraphs: ["^Changelog:"]
        """).strip() + "\n",
    )

    # контексты
    write(root / "lg-cfg" / "contexts" / "a.tpl.md", "Intro\n\n${docs}\n")
    write(root / "lg-cfg" / "contexts" / "b.tpl.md", "X ${tpl:a} Y ${all}\n")

    # файлы для матчинга targets
    write(root / "pkg" / "mod.py", "def foo():\n    pass\n")
    write(root / "docs" / "note.md", "# T\n\nChangelog: ...\n\nBody.\n")
    return root

def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )

def jload(s: str):
    return json.loads(s)

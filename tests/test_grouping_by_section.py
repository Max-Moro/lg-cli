import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path


def _w(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")
    return p


def _run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )


def test_grouping_respects_sections(tmp_path: Path):
    root = tmp_path
    # Конфиг: две секции docs и code, каждая ограничена своим поддеревом
    _w(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent("""
        docs:
          extensions: [".md"]
          code_fence: false
          filters:
            mode: allow
            allow:
              - "/docs/**"
        code:
          extensions: [".md"]
          code_fence: false
          filters:
            mode: allow
            allow:
              - "/code/**"
        """).strip() + "\n",
    )
    # Контекст использует обе секции
    _w(root / "lg-cfg" / "mix.ctx.md", "${docs}\n\n${code}\n")

    # docs → два файла .md
    _w(root / "docs" / "a.md", "# A\n\nText\n")
    _w(root / "docs" / "b.md", "## B\n\nMore\n")
    # code → один файл .md
    _w(root / "code" / "only.md", "# Only\n")

    # Прогоняем report, чтобы получить метаданные файлов
    cp = _run_cli(root, "report", "ctx:mix")
    assert cp.returncode == 0, cp.stderr
    data = json.loads(cp.stdout)
    files = {row["path"]: row for row in data["files"]}

    # Убедимся, что все 3 файла попали
    assert "docs/a.md" in files
    assert "docs/b.md" in files
    assert "code/only.md" in files

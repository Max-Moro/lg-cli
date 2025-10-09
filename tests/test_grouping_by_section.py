import json
import textwrap
from pathlib import Path

from tests.infrastructure import write, run_cli


def test_grouping_respects_sections(tmp_path: Path):
    root = tmp_path
    # Конфиг: две секции docs и code, каждая ограничена своим поддеревом
    write(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent("""
        docs:
          extensions: [".md"]
          filters:
            mode: allow
            allow:
              - "/docs/**"
        code:
          extensions: [".md"]
          filters:
            mode: allow
            allow:
              - "/code/**"
        """).strip() + "\n",
    )
    # Контекст использует обе секции
    write(root / "lg-cfg" / "mix.ctx.md", "${docs}\n\n${code}\n")

    # docs → два файла .md
    write(root / "docs" / "a.md", "# A\n\nText\n")
    write(root / "docs" / "b.md", "## B\n\nMore\n")
    # code → один файл .md
    write(root / "code" / "only.md", "# Only\n")

    # Прогоняем report, чтобы получить метаданные файлов
    cp = run_cli(root, "report", "ctx:mix")
    assert cp.returncode == 0, cp.stderr
    data = json.loads(cp.stdout)
    files = {row["path"]: row for row in data["files"]}

    # Убедимся, что все 3 файла попали
    assert "docs/a.md" in files
    assert "docs/b.md" in files
    assert "code/only.md" in files

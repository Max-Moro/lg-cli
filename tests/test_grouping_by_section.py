import textwrap
from pathlib import Path

from tests.infrastructure import write, run_cli, jload


def test_grouping_respects_sections(tmp_path: Path):
    root = tmp_path
    # Config: two sections docs and code, each limited to its own subtree
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
    # Context uses both sections
    write(root / "lg-cfg" / "mix.ctx.md", "${docs}\n\n${code}\n")

    # docs - two .md files
    write(root / "docs" / "a.md", "# A\n\nText\n")
    write(root / "docs" / "b.md", "## B\n\nMore\n")
    # code - one .md file
    write(root / "code" / "only.md", "# Only\n")

    # Run report to get file metadata
    cp = run_cli(root, "report", "ctx:mix")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    files = {row["path"]: row for row in data["files"]}

    # Ensure all 3 files are included
    assert "docs/a.md" in files
    assert "docs/b.md" in files
    assert "code/only.md" in files

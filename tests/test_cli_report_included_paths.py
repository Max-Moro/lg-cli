import textwrap
from .infrastructure import run_cli, jload

def test_cli_report_included_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # ├── keep.py
    # ├── ignore.log
    # └── secure/
    #       ├── __init__.py  (trivial -> filtered by adapter)
    #       ├── inner_keep.py
    #       └── nope.md
    (tmp_path / "keep.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "ignore.log").write_text("", encoding="utf-8")
    (tmp_path / "secure").mkdir()
    (tmp_path / "secure/__init__.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "secure/inner_keep.py").write_text("print('ok_inner')", encoding="utf-8")
    (tmp_path / "secure/nope.md").write_text("", encoding="utf-8")

    # config: one section all, only .py, fencing enabled,
    # block *.log, and in secure/ allow only *.py
    (tmp_path / "lg-cfg").mkdir()
    (tmp_path / "lg-cfg/sections.yaml").write_text(textwrap.dedent("""
      all:
        extensions: [".py"]
        filters:
          mode: block
          block: ["**/*.log"]
          children:
            secure:
              mode: allow
              allow: ["*.py"]
    """).strip() + "\n", encoding="utf-8")

    # Request report for virtual section context
    cp = run_cli(tmp_path, "report", "sec:all")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)

    # Collect paths that really made it into the report (after adapters)
    paths = {f["path"] for f in data["files"]}
    assert paths == {"keep.py", "secure/inner_keep.py"}

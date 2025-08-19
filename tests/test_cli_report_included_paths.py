import textwrap
from .conftest import run_cli, jload

def test_cli_report_included_paths_vnext(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # ├── keep.py
    # ├── ignore.log
    # └── secure/
    #       ├── __init__.py  (тривиальный → отфильтрует адаптер)
    #       ├── inner_keep.py
    #       └── nope.md
    (tmp_path / "keep.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "ignore.log").write_text("", encoding="utf-8")
    (tmp_path / "secure").mkdir()
    (tmp_path / "secure/__init__.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "secure/inner_keep.py").write_text("print('ok_inner')", encoding="utf-8")
    (tmp_path / "secure/nope.md").write_text("", encoding="utf-8")

    # config: одна секция all, только .py, fencing включён,
    # блокируем *.log, а в secure/ разрешаем только *.py
    (tmp_path / "lg-cfg").mkdir()
    (tmp_path / "lg-cfg/config.yaml").write_text(textwrap.dedent("""
      schema_version: 6
      all:
        extensions: [".py"]
        code_fence: true
        filters:
          mode: block
          block: ["**/*.log"]
          children:
            secure:
              mode: allow
              allow: ["*.py"]
    """).strip() + "\n", encoding="utf-8")

    # Запрашиваем отчёт по виртуальному контексту секции
    cp = run_cli(tmp_path, "report", "sec:all")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)

    # Собираем пути, которые реально попали в отчёт (после адаптеров)
    paths = {f["path"] for f in data["files"]}
    assert paths == {"keep.py", "secure/inner_keep.py"}

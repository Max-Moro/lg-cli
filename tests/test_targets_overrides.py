from pathlib import Path
from .conftest import run_cli, jload, write


def test_per_file_adapter_overrides_propagate(tmpproj: Path, monkeypatch):
    """Проверяем, что targets применяются и ключи оверрайдов попадают в meta."""
    monkeypatch.chdir(tmpproj)

    # Подготовим файлы под таргеты секции:
    write(Path("pkg/mod.py"), "def foo():\n    pass\n")
    write(Path("docs/note.md"), "# T\n\nChangelog: ...\n\nBody.\n")

    cp = run_cli(Path("."), "report", "sec:all")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    files = {f["path"]: f for f in data["files"]}
    # наш python-файл в pkg должен нести след о том, что передан strip_function_bodies
    py_meta = files.get("pkg/mod.py", {}).get("meta", {})
    keys = py_meta.get("_adapter_cfg_keys", "")
    assert "strip_function_bodies" in keys

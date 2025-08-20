from pathlib import Path

from lg.adapters import get_adapter_for_path


def test_python_adapter_registered_and_selected(tmp_path: Path):
    py_file = tmp_path / "foo.py"
    py_file.write_text("pass", encoding="utf-8")
    adapter_cls = get_adapter_for_path(py_file)
    assert adapter_cls.name == "python"

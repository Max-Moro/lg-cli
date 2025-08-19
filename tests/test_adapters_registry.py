from pathlib import Path

from lg.adapters.base import _ADAPTERS_BY_NAME, get_adapter_for_path

def test_base_adapter_registered():
    assert "base" in _ADAPTERS_BY_NAME

def test_python_adapter_registered_and_selected(tmp_path: Path):
    py_file = tmp_path / "foo.py"
    py_file.write_text("pass", encoding="utf-8")
    adapter = get_adapter_for_path(py_file)
    assert adapter.name == "python"

from pathlib import Path
from lg.core.generator import generate_listing

def test_trivial_init(tmp_path: Path, capsys):
    # создаём искусственный проект
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/__init__.py").write_text("pass\n")

    generate_listing(root=tmp_path, cfg={"skip_trivial_inits": True}, mode="all")
    captured = capsys.readouterr().out
    assert "__init__.py" not in captured          # файл пропущен

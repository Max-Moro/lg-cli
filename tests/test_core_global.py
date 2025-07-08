from pathlib import Path
from lg.core.generator import generate_listing

def _run(root: Path, cfg: dict) -> str:
    from io import StringIO, TextIOWrapper
    import sys
    buf = StringIO()
    _stdout: TextIOWrapper = sys.stdout
    sys.stdout = buf
    try:
        generate_listing(root=root, cfg=cfg, mode="all")
    finally:
        sys.stdout = _stdout
    return buf.getvalue()

def test_global_skip_empty_without_adapter(tmp_path: Path):
    # создаём файл .txt (адаптера нет)
    (tmp_path / "data.txt").write_text("")
    out = _run(tmp_path, cfg={"skip_empty": True})
    # файл должен быть пропущен
    assert "FILE: data.txt" not in out

def test_global_skip_empty_ignored_for_python(tmp_path: Path):
    (tmp_path / "m.py").write_text("")            # пустой .py
    cfg = {
        "skip_empty": True,               # глобально просим пропускать
        "python": { "skip_empty": False } # но для Python включаем
    }
    out = _run(tmp_path, cfg=cfg)
    # .py должен присутствовать, глобальное правило не применилось
    assert "FILE: m.py" in out

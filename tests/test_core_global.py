from pathlib import Path
from io import StringIO, TextIOWrapper
import sys

from lg.core.generator import generate_listing
from lg.config import Config
from lg.adapters.python import LangPython


def _run(root: Path, cfg: Config) -> str:
    """Запускаем генератор и перехватываем stdout."""
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

    cfg = Config(skip_empty=True)

    out = _run(tmp_path, cfg)
    # файл должен быть пропущен
    assert "FILE: data.txt" not in out


def test_global_skip_empty_ignored_for_python(tmp_path: Path):
    (tmp_path / "m.py").write_text("")  # пустой .py

    cfg = Config(
        skip_empty=True,                          # глобально просим пропускать
        python=LangPython(skip_empty=False)       # но для Python отключаем правило
    )

    out = _run(tmp_path, cfg)
    # .py должен присутствовать, глобальное правило не применилось
    assert "FILE: m.py" in out

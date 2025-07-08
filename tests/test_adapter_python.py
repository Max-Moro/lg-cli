from pathlib import Path
from io import StringIO
import sys

from lg.core.generator import generate_listing
from lg.config import Config, LangPython


def _listing(root: Path, cfg: Config) -> str:
    """Запускаем генератор и перехватываем stdout."""
    buf = StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        generate_listing(root=root, cfg=cfg, mode="all")
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


def test_trivial_init_skipped(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("pass\n")

    cfg = Config(
        python=LangPython(skip_trivial_inits=True)
    )

    out = _listing(tmp_path, cfg)
    assert "__init__.py" not in out


def test_non_trivial_init_kept(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("VERSION = '1.0'")

    cfg = Config(
        python=LangPython(skip_trivial_inits=True)
    )

    out = _listing(tmp_path, cfg)
    assert "FILE: pkg/__init__.py" in out

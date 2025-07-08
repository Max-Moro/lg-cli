from pathlib import Path
from lg.core.generator import generate_listing

def _listing(root: Path, cfg: dict) -> str:
    import io, sys
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        generate_listing(root=root, cfg=cfg, mode="all")
    finally:
        sys.stdout = old
    return buf.getvalue()

def test_trivial_init_skipped(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("pass\n")
    cfg = { "python": { "skip_trivial_inits": True } }
    out = _listing(tmp_path, cfg)
    assert "__init__.py" not in out

def test_non_trivial_init_kept(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("VERSION = '1.0'")
    cfg = { "python": { "skip_trivial_inits": True } }
    out = _listing(tmp_path, cfg)
    assert "FILE: pkg/__init__.py" in out

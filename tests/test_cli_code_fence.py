import os
import sys
from dataclasses import asdict
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from lg.cli import main as cli_main
from lg.config import Config, SCHEMA_VERSION, DEFAULT_SECTION_NAME
from lg.filters.model import FilterNode


def _run_cli_capture(tmp_path: Path, cfg: Config, *cli_args: str) -> str:
    # cwd → tmp
    orig_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # config.yaml
        cfg_dir = tmp_path / "lg-cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        YAML().dump(
            {"schema_version": SCHEMA_VERSION, DEFAULT_SECTION_NAME: asdict(cfg)},
            (cfg_dir / "config.yaml").open("w", encoding="utf-8"),
        )
        # stdout capture
        buf = StringIO()
        argv_orig, stdout_orig = sys.argv, sys.stdout
        sys.argv, sys.stdout = ["listing-generator", *cli_args], buf
        try:
            try:
                cli_main()
            except SystemExit:
                pass
        finally:
            sys.argv, sys.stdout = argv_orig, stdout_orig
        return buf.getvalue()
    finally:
        os.chdir(orig_cwd)


def test_no_code_fence_overrides_config(tmp_path: Path):
    # данные
    (tmp_path / "m.py").write_text("print('x')\n", encoding="utf-8")
    cfg = Config(
        extensions=[".py"],
        filters=FilterNode(mode="block"),
        code_fence=True,    # включено в конфиге
    )

    # Без флага — fence есть
    out1 = _run_cli_capture(tmp_path, cfg, "--section", "all")
    assert "```python" in out1

    # С флагом --no-code-fence — fence нет, но маркер файла печатается
    out2 = _run_cli_capture(tmp_path, cfg, "--section", "all", "--no-code-fence")
    assert "```python" not in out2
    assert "# —— FILE: m.py ——" in out2

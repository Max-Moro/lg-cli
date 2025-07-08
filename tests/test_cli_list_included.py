# tests/test_cli_list_included.py
from pathlib import Path
from io import StringIO
import sys
from dataclasses import asdict

from lg.cli import main as cli_main
from lg.config import Config
from lg.filters.model import FilterNode


def _run_cli(tmp_path: Path, cfg: Config, *cli_args: str) -> str:
    # Записываем сериализованный dataclass в YAML
    cfg_path = tmp_path / "listing_config.yaml"
    from ruamel.yaml import YAML

    with cfg_path.open("w", encoding="utf-8") as f:
        YAML().dump(asdict(cfg), f)

    # Подменяем argv и собираем вывод
    argv_orig = sys.argv
    sys.argv = ["listing-generator", "--root", str(tmp_path), "--list-included", *cli_args]
    buf = StringIO()
    stdout_orig = sys.stdout
    sys.stdout = buf
    try:
        cli_main()
    finally:
        sys.argv = argv_orig
        sys.stdout = stdout_orig
    return buf.getvalue()


def test_list_included_outputs_correct_paths(tmp_path: Path):
    # ├── keep.py
    # ├── ignore.log
    # └── secure/
    #       ├── ok.py
    #       └── nope.md
    (tmp_path / "keep.py").write_text("print('ok')")
    (tmp_path / "ignore.log").write_text("")
    secure = tmp_path / "secure"
    secure.mkdir()
    (secure / "ok.py").write_text("")
    (secure / "nope.md").write_text("")

    cfg = Config(
        filters=FilterNode(
            mode="block",
            block=["**/*.log"],
            children={
                "secure": FilterNode(
                    mode="allow",
                    allow=["*.py"],
                )
            },
        )
    )

    out = _run_cli(tmp_path, cfg)
    paths = set(out.strip().splitlines())
    assert paths == {"keep.py", "secure/ok.py"}

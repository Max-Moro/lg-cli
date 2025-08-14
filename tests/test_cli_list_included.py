import os
import sys
from dataclasses import asdict
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from lg.cli import main as cli_main
from lg.config import Config, SCHEMA_VERSION, DEFAULT_SECTION_NAME
from lg.filters.model import FilterNode


def _run_cli(tmp_path: Path, cfg: Config, *cli_args: str) -> str:
    # Переключаемся в tmp_path
    orig_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Пишем мультисекционный конфиг в lg-cfg/config.yaml
        cfg_dir = tmp_path / "lg-cfg"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "config.yaml"
        sections = {
            "schema_version": SCHEMA_VERSION,
            DEFAULT_SECTION_NAME: asdict(cfg),
        }
        YAML().dump(sections, cfg_path.open("w", encoding="utf-8"))

        # Запускаем CLI с --list-included
        argv_orig = sys.argv
        sys.argv = ["listing-generator", "--list-included", *cli_args]
        buf = StringIO()
        stdout_orig = sys.stdout
        sys.stdout = buf
        try:
            # main() может sys.exit(), ловим, но не прерываем тест
            cli_main()
        except SystemExit:
            pass
        finally:
            sys.argv = argv_orig
            sys.stdout = stdout_orig

        return buf.getvalue()
    finally:
        os.chdir(orig_cwd)


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
    (secure / "__init__.py").write_text("")
    (secure / "inner_keep.py").write_text("print('ok_inner')")
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
    assert paths == {"keep.py", "secure/inner_keep.py"}

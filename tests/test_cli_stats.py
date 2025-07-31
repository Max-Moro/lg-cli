import os
import re
import sys
from dataclasses import asdict
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from lg.cli import main as cli_main
from lg.config import Config, SCHEMA_VERSION, DEFAULT_SECTION_NAME
from lg.filters.model import FilterNode


def _run(tmp_path: Path, cfg: Config, *args: str) -> str:
    # пишем cfg
    cfg_dir = tmp_path / "lg-cfg"
    cfg_dir.mkdir(parents=True)
    YAML().dump(
        {"schema_version": SCHEMA_VERSION, DEFAULT_SECTION_NAME: asdict(cfg)},
        (cfg_dir / "config.yaml").open("w", encoding="utf-8"),
    )
    # файлы
    (tmp_path / "a.py").write_text("print('a')\n")
    (tmp_path / "big.txt").write_text("x" * 4000)

    # run cli (меняем cwd → tmp_path, как в других тестах)
    orig_cwd = os.getcwd()
    os.chdir(tmp_path)
    argv = ["listing-generator", "--list-included", "--stats", *args]
    buf = StringIO()
    sys.argv, old = argv, sys.stdout
    sys.stdout = buf
    try:
        try:
            cli_main()
        except SystemExit:
            pass
    finally:
        sys.argv, sys.stdout = ["python"], old
        os.chdir(orig_cwd)
    return buf.getvalue()


def test_stats_table(tmp_path: Path):
    # разрешаем .txt, иначе big.txt отфильтруется
    cfg = Config(
        extensions=[".py", ".txt"],
        filters=FilterNode(mode="block"),
    )
    out = _run(tmp_path, cfg, "--sort", "size", "--model", "o3")
    # таблица содержит заголовок PATH и TOTAL-строку
    assert "PATH" in out and "TOTAL" in out
    # обе строки файлов
    assert any(re.search(r"a\.py", ln) for ln in out.splitlines())
    assert any(re.search(r"big\.txt", ln) for ln in out.splitlines())

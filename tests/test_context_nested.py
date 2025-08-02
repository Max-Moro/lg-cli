import os, sys
from pathlib import Path

import pytest

from lg.context import generate_context


class DummyCfg:
    def __init__(self, name): self.section_name = name


def _write(ctx_dir: Path, rel: str, body: str):
    p = ctx_dir / f"{rel}.tmpl.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_nested_context_ok(tmp_path: Path, capsys, monkeypatch):
    # 1) структура шаблонов
    ctx_dir = tmp_path / "lg-cfg" / "contexts"
    _write(ctx_dir, "leaf", "LEAF ${sec}")
    _write(ctx_dir, "mid/inner", "MIDDLE\n${tpl:leaf}\n")
    _write(ctx_dir, "root", "ROOT\n${tpl:mid/inner}\n")

    # 2) fake generate_listing -> печатает "LISTING[<name>]"
    import lg.context as ctx_mod
    monkeypatch.setattr(
        ctx_mod,
        "generate_listing",
        lambda root, cfg, mode, list_only=False: sys.stdout.write(f"LISTING[{cfg.section_name}]"),
    )

    # 3) конфиги
    cfgs = {"sec": DummyCfg("sec")}

    # 4) запуск
    os.chdir(tmp_path)
    generate_context("root", cfgs)
    out = capsys.readouterr().out

    assert "ROOT" in out
    assert "MIDDLE" in out
    assert "LEAF LISTING[sec]" in out


def test_cycle_detection(tmp_path: Path):
    ctx_dir = tmp_path / "lg-cfg" / "contexts"
    _write(ctx_dir, "a", "A -> ${tpl:b}")
    _write(ctx_dir, "b", "B -> ${tpl:a}")

    os.chdir(tmp_path)
    with pytest.raises(RuntimeError) as ei:
        generate_context("a", {})
    assert "cycle detected" in str(ei.value).lower()

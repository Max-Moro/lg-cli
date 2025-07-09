import sys

import pytest

import lg.cli as cli_mod
from lg.config import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    # Переносим cwd в tmp_path
    monkeypatch.chdir(tmp_path)

    # Готовим структуру lg-cfg/
    cfg_dir = tmp_path / "lg-cfg"
    (cfg_dir / "contexts").mkdir(parents=True)

    # Простейший config.yaml с одной секцией 'sec'
    (cfg_dir / "config.yaml").write_text(
        f"schema_version: {SCHEMA_VERSION}\nsec: {{}}\n"
    )

    # Шаблон contexts/ctx.tmpl.md
    (cfg_dir / "contexts" / "ctx.tmpl.md").write_text(
        "Hello ${sec}"
    )

    # Подменяем generate_listing внутри lg.context на stub,
    # чтобы generate_context печатал «OK» вместо реальных листингов.
    import lg.context as ctx_mod
    monkeypatch.setattr(
        ctx_mod,
        "generate_listing",
        lambda **kw: sys.stdout.write("OK"),
    )

    return tmp_path


def run_cli(args):
    """
    Вызывает cli_mod.main() с заданными args.
    Возвращает код выхода: 0 при нормальном возврате main(),
    или se.code при SystemExit.
    """
    orig_argv = sys.argv[:]
    sys.argv = ["listing-generator"] + args
    try:
        try:
            cli_mod.main()
            return 0
        except SystemExit as se:
            # Если код не указан, считаем его 1
            return se.code if se.code is not None else 1
    finally:
        sys.argv = orig_argv


def test_cli_context_prints(capsys):
    code = run_cli(["--context", "ctx"])
    # При успешном выполнении код 0, в stdout — «OK»
    assert code == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_cli_context_list_included(capsys):
    # Флаг --list-included тоже прокидывается и не ломает
    code = run_cli(["--context", "ctx", "--list-included"])
    assert code == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_cli_missing_context_returns_error():
    # Шаблон ctx2 не существует → sys.exit(1)
    code = run_cli(["--context", "ctx2"])
    assert code != 0

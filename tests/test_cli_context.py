import sys

import pytest

import lg.cli as cli_mod


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch, tmp_path):
    # Переносим cwd в tmp_path
    monkeypatch.chdir(tmp_path)
    # Подготовим структуру lg-cfg
    cfg_dir = tmp_path / 'lg-cfg'
    (cfg_dir / 'contexts').mkdir(parents=True)
    # простой config.yaml
    (cfg_dir / 'config.yaml').write_text('schema_version: 4\nsec: {}')
    # шаблон
    (cfg_dir / 'contexts' / 'ctx.tmpl.md').write_text('Hello ${sec}')
    # Подменяем load_config и generate_listing
    import lg.context as ctx_mod
    monkeypatch.setattr(ctx_mod, 'generate_listing', lambda **kw: sys.stdout.write('OK'))
    def fake_load_config(path, section):
        class C: pass
        c = C()
        c.section_name = section
        return c
    monkeypatch.setattr(ctx_mod, 'load_config', fake_load_config)
    return tmp_path

def run_cli(args):
    orig_argv = sys.argv[:]
    sys.argv = ['listing-generator'] + args
    try:
        with pytest.raises(SystemExit) as se:
            cli_mod.main()
    finally:
        sys.argv = orig_argv
    return se.value.code

def test_cli_context_prints(monkeypatch, capsys):
    code = run_cli(['--context', 'ctx'])
    # код 0, и в stdout «OK»
    out = capsys.readouterr().out
    assert code == 0
    assert 'OK' in out

def test_cli_context_list_included(monkeypatch, capsys):
    # флаг --list-included должен тоже пройти и дать «OK»
    code = run_cli(['--context', 'ctx', '--list-included'])
    out = capsys.readouterr().out
    assert code == 0
    assert 'OK' in out

def test_cli_missing_section(monkeypatch):
    # вызываем несуществующий контекст ctx2 → код != 0
    code = run_cli(['--context', 'ctx2'])
    assert code != 0

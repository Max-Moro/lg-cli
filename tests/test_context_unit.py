import sys

import pytest

from lg.context import ContextTemplate, generate_context


class Dummy:
    """Заглушка вместо real generate_listing, возвращает простой маркер."""
    @staticmethod
    def fake_generate(root, cfg, mode, list_only=False):
        # возвращает разные строки для разных секций
        sec = cfg
        name = getattr(cfg, 'section_name', 'unknown')
        if name == 'empty':
            return ''
        return f'CONTENT_OF_{name}'


@pytest.fixture(autouse=True)
def patch_generator(monkeypatch):
    # Подменяем реальный generate_listing: он печатает в stdout,
    # а мы просто возвращаем строку из fake_generate.
    import lg.context as ctx_mod

    def fake_generate_context_output(root, cfg, mode, list_only=False):
        # эмулируем вывод в stdout, но вернув строку сразу
        sec = cfg
        # ожидаем, что в cfg есть атрибут section_name
        text = f'LISTING[{sec.section_name}]'
        sys.stdout.write(text)

    monkeypatch.setattr(ctx_mod, 'generate_listing', fake_generate_context_output)
    yield


def write_cfg(tmp_path, sections):
    """Собирает lg-cfg/config.yaml из словаря секций→None."""
    cfg_dir = tmp_path / 'lg-cfg'
    # гарантируем, что contexts директория есть (не падаем, если уже создана)
    (cfg_dir / 'contexts').mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / 'config.yaml'
    # простейший yaml с двумя секциями, без реальных фильтров
    lines = ['schema_version: 4']
    for name in sections:
        lines.append(f'{name}: {{}}')
    cfg_file.write_text('\n'.join(lines))
    return cfg_dir


def write_template(cfg_dir, name, content):
    tmpl = cfg_dir / 'contexts' / f'{name}.tmpl.md'
    tmpl.write_text(content)


def test_context_template_allows_hyphens():
    t = ContextTemplate('Hello ${foo-bar} and ${baz_123}')
    # должно найти оба плейсхолдера
    subs = {'foo-bar': 'X', 'baz_123': 'Y'}
    assert t.substitute(subs) == 'Hello X and Y'


def test_generate_context_success(tmp_path, monkeypatch, capsys):
    # создаём конфиг с двумя секциями
    cfg_dir = write_cfg(tmp_path, ['docs', 'empty'])
    # шаблон со вставками обеих
    write_template(cfg_dir, 'ctx', 'D: ${docs}\nE: ${empty}')

    # chdir в tmp_path
    monkeypatch.chdir(tmp_path)
    # подменяем load_config, чтобы cfg.section_name был доступен
    import lg.context as ctx_mod
    def fake_load_config(path, section):
        class Cfg: pass
        cfg = Cfg()
        cfg.section_name = section
        return cfg
    monkeypatch.setattr(ctx_mod, 'load_config', fake_load_config)

    # вызываем
    generate_context('ctx')
    out = capsys.readouterr().out
    # из fake_generate_context_output для docs и empty
    assert 'LISTING[docs]' in out
    assert 'LISTING[empty]' in out


@pytest.mark.parametrize('missing', ['config', 'template'])
def test_missing_files_raise(tmp_path, monkeypatch, missing):
    """
    Если нет config.yaml или нет шаблона, generate_context должен упасть.
    """
    cfg_dir = tmp_path / 'lg-cfg'
    # уверены, что папка contexts существует (чтобы не смешивать ошибки)
    (cfg_dir / 'contexts').mkdir(parents=True, exist_ok=True)

    if missing == 'config':
        # пропускаем создание config.yaml => должно упасть на его отсутствие
        pass
    else:
        # создаём config.yaml, но НЕ создаём шаблон => должно упасть на отсутствие шаблона
        write_cfg(tmp_path, ['docs'])

    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        generate_context('ctx')


def test_unknown_section_raises(tmp_path, monkeypatch):
    # есть только секция docs
    cfg_dir = write_cfg(tmp_path, ['docs'])
    # шаблон с незнакомым
    write_template(cfg_dir, 'ctx', 'X: ${unknown}')
    monkeypatch.chdir(tmp_path)
    # подмена list_sections, load_config
    import lg.context as ctx_mod
    monkeypatch.setattr(ctx_mod, 'list_sections', lambda path: ['docs'])
    with pytest.raises(RuntimeError) as ei:
        generate_context('ctx')
    assert "Section 'unknown' not found" in str(ei.value)

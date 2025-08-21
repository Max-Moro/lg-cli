import textwrap
from pathlib import Path

from .conftest import run_cli


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_labels_auto_strip_common_prefix_and_uniquify(tmpproj: Path):
    """
    Создаём секцию cli-src с общим префиксом 'cli/' и коллизиями basename 'engine.py'.
    Ожидаем:
      - общий 'cli/' снят,
      - 'lg/engine.py' и 'io/engine.py' различаются,
      - одинокие файлы печатаются коротко (например, 'pyproject.toml').
    """
    root = tmpproj
    # Переопределяем config: добавляем новую секцию cli-src
    cfg = (root / "lg-cfg" / "config.yaml").read_text(encoding="utf-8")
    cfg += textwrap.dedent(
        """

        cli-src:
          extensions: [".py", ".toml"]
          filters:
            mode: allow
            allow:
              - "/cli/"
          path_labels: auto
        """
    )
    (root / "lg-cfg" / "config.yaml").write_text(cfg, encoding="utf-8")

    # Структура файлов
    _write(root / "cli" / "pyproject.toml", "[project]\nname='x'\n")
    _write(root / "cli" / "lg" / "engine.py", "print('lg')\n")
    _write(root / "cli" / "io" / "engine.py", "print('io')\n")
    _write(root / "cli" / "lg" / "util.py", "print('u')\n")

    # Виртуальный контекст секции
    cp = run_cli(root, "render", "sec:cli-src")
    assert cp.returncode == 0, cp.stderr
    out = cp.stdout
    # Префикс 'cli/' должен быть снят
    assert "# —— FILE: pyproject.toml ——" in out
    assert "# —— FILE: lg/engine.py ——" in out
    assert "# —— FILE: io/engine.py ——" in out
    assert "# —— FILE: lg/util.py ——" in out
    # Не должно встретиться исходного 'cli/lg/engine.py'
    assert "# —— FILE: cli/lg/engine.py ——" not in out


def test_labels_basename_mode_uniquify(tmpproj: Path):
    """
    В режиме basename все метки стартуют с одного basename и затем уникализируются суффиксом директорий.
    """
    root = tmpproj
    cfg = (root / "lg-cfg" / "config.yaml").read_text(encoding="utf-8")
    cfg += textwrap.dedent(
        """

        vs-src:
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/vscode/"
          path_labels: basename
        """
    )
    (root / "lg-cfg" / "config.yaml").write_text(cfg, encoding="utf-8")

    _write(root / "vscode" / "a" / "engine.py", "a=1\n")
    _write(root / "vscode" / "b" / "engine.py", "b=1\n")
    _write(root / "vscode" / "x.py", "x=1\n")

    cp = run_cli(root, "render", "sec:vs-src")
    assert cp.returncode == 0, cp.stderr
    out = cp.stdout
    assert "# —— FILE: a/engine.py ——" in out
    assert "# —— FILE: b/engine.py ——" in out
    # одиночный файл печатается basename'ом
    assert "# —— FILE: x.py ——" in out

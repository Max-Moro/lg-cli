import sys
from io import StringIO
from pathlib import Path

from lg.config import Config
from lg.core.generator import generate_listing
from lg.filters.engine import FilterEngine
from lg.filters.model import FilterNode


def _engine():
    # корень default-allow, но блочим *.log
    root = FilterNode(
        mode="block",
        block=["**/*.log"],
        children={
            "secure": FilterNode(
                mode="allow",
                allow=["*.py"],
                block=["*_secret.py"],
            )
        },
    )
    return FilterEngine(root)


def test_block_global_log():
    eng = _engine()
    assert eng.includes("src/app.py")
    assert not eng.includes("src/debug.log")


def test_secure_allow_only_py():
    eng = _engine()
    assert eng.includes("secure/auth.py")
    assert not eng.includes("secure/readme.md")
    assert not eng.includes("secure/data_secret.py")

def test_nested_allow_subtree_only_whitelist():
    """
    Вложенные mode: allow должны работать как «жёсткий фильтр»:
    дочерний allow сужает родительский и отсекает всё не перечисленное.
    """
    root = FilterNode(
        mode="allow",
        allow=["vscode-lg/"],  # разрешаем только поддерево vscode-lg/
        children={
            "vscode-lg": FilterNode(
                mode="allow",
                # разрешаем только src/** и конкретные файлы в корне поддерева
                allow=[
                    "src/**",
                    "package.json",
                    "tsconfig.json",
                ],
            )
        },
    )
    eng = FilterEngine(root)

    # ✅ разрешённые пути внутри vscode-lg/
    assert eng.includes("vscode-lg/src/extension.ts")
    assert eng.includes("vscode-lg/src/client/start.ts")
    assert eng.includes("vscode-lg/package.json")
    assert eng.includes("vscode-lg/tsconfig.json")

    # ❌ запрещённые пути внутри vscode-lg/ (не перечислены в дочернем allow)
    assert not eng.includes("vscode-lg/node_modules/lodash/index.js")
    assert not eng.includes("vscode-lg/README.md")
    assert not eng.includes("vscode-lg/yarn.lock")

    # ❌ за пределами корневого allow поддерева — тоже запрещено
    assert not eng.includes("somewhere_else/file.ts")

def test_may_descend_allow_specific_file():
    """
    Регресс-тест: если в allow указан конкретный файл (напр. /lg/README.md),
    прунер обязан разрешить спуск в каталог 'lg'.
    """
    root = FilterNode(
        mode="allow",
        allow=["/lg/README.md"],
    )
    eng = FilterEngine(root)
    assert eng.may_descend("lg") is True
    # а вот в соседние каталоги спускаться смысла нет
    assert eng.may_descend("docs") is False


def test_listing_with_allow_specific_file(tmp_path: Path):
    """
    Сквозной тест генератора: при конфиге mode:allow + allow:/lg/README.md
    файл должен попасть в листинг.
    """
    # ── подготовка файловой структуры
    (tmp_path / "lg").mkdir()
    (tmp_path / "lg" / "README.md").write_text("# Hello from LG README\nBody\n", encoding="utf-8")
    # «шум» рядом, который не должен попадать
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "note.md").write_text("noise", encoding="utf-8")

    # ── конфигурация: листим только .md, и только конкретный файл
    cfg = Config(
        extensions=[".md"],
        # фильтр: разрешаем строго /lg/README.md
        filters=FilterNode(mode="allow", allow=["/lg/README.md"]),
        # fenced-блоки не важны: это чистый Markdown, генератор сам их отключит
    )

    # ── захват stdout
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        generate_listing(root=tmp_path, cfg=cfg, mode="all")
    finally:
        sys.stdout = old

    out = buf.getvalue()
    # В чистом Markdown режимe путь файла не печатается, поэтому проверяем содержимое
    assert "Hello from LG README" in out
    assert "Body" in out
    # И убеждаемся, что «шум» не попал
    assert "noise" not in out
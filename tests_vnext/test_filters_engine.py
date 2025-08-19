from pathlib import Path
from lg.io.filters import FilterEngine
from lg.io.model import FilterNode
from lg.engine import run_render
from lg.types import RunOptions

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
    Вложенные mode:allow работают как «жёсткий фильтр»: дочерний allow сужает родительский.
    """
    root = FilterNode(
        mode="allow",
        allow=["vscode-lg/"],  # разрешаем только поддерево vscode-lg/
        children={
            "vscode-lg": FilterNode(
                mode="allow",
                allow=[
                    "src/**",
                    "package.json",
                    "tsconfig.json",
                ],
            )
        },
    )
    eng = FilterEngine(root)

    # ✅ разрешённые пути
    assert eng.includes("vscode-lg/src/extension.ts")
    assert eng.includes("vscode-lg/src/client/start.ts")
    assert eng.includes("vscode-lg/package.json")
    assert eng.includes("vscode-lg/tsconfig.json")

    # ❌ не перечисленное в дочернем allow — запрещено
    assert not eng.includes("vscode-lg/node_modules/lodash/index.js")
    assert not eng.includes("vscode-lg/README.md")
    assert not eng.includes("vscode-lg/yarn.lock")

    # ❌ за пределами корневого allow — запрещено
    assert not eng.includes("somewhere_else/file.ts")

def test_may_descend_allow_specific_file():
    """
    Регресс: если в allow указан конкретный файл (/lg/README.md),
    прунер обязан разрешить спуск в каталог 'lg'.
    """
    root = FilterNode(
        mode="allow",
        allow=["/lg/README.md"],
    )
    eng = FilterEngine(root)
    assert eng.may_descend("lg") is True
    assert eng.may_descend("docs") is False

def test_render_with_allow_specific_file(tmp_path: Path, monkeypatch):
    """
    Сквозной тест: при секции mode:allow + allow:/lg/README.md
    файл попадает в рендер секции, «шум» — нет.
    """
    # ── файловая структура
    (tmp_path / "lg").mkdir()
    (tmp_path / "lg" / "README.md").write_text("# Hello from LG README\nBody\n", encoding="utf-8")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "note.md").write_text("noise", encoding="utf-8")

    # ── конфиг: одна секция all
    (tmp_path / "lg-cfg").mkdir()
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        "schema_version: 6\n"
        "all:\n"
        "  extensions: ['.md']\n"
        "  code_fence: false\n"        # md-only → без fenced/маркеров
        "  filters:\n"
        "    mode: allow\n"
        "    allow: ['/lg/README.md']\n",
        encoding="utf-8"
    )

    # ── запуск пайплайна vNext (виртуальный контекст секции)
    monkeypatch.chdir(tmp_path)
    doc = run_render("sec:all", RunOptions(code_fence=False))
    out = doc.text

    # В чистом MD режиме путь файла не печатается — проверяем содержимое
    assert "Hello from LG README" in out
    assert "Body" in out
    assert "noise" not in out

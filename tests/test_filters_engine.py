from pathlib import Path
from lg.filtering.filters import FilterEngine
from lg.filtering.model import FilterNode
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
        allow=["vscode-ext/"],  # разрешаем только поддерево vscode-ext/
        children={
            "vscode-ext": FilterNode(
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
    assert eng.includes("vscode-ext/src/extension.ts")
    assert eng.includes("vscode-ext/src/client/start.ts")
    assert eng.includes("vscode-ext/package.json")
    assert eng.includes("vscode-ext/tsconfig.json")

    # ❌ не перечисленное в дочернем allow — запрещено
    assert not eng.includes("vscode-ext/node_modules/lodash/index.js")
    assert not eng.includes("vscode-ext/README.md")
    assert not eng.includes("vscode-ext/yarn.lock")

    # ❌ за пределами корневого allow — запрещено
    assert not eng.includes("somewhere_else/file.ts")

def test_may_descend_allow_specific_file():
    """
    Регресс: если в allow указан конкретный файл (/core/README.md),
    прунер обязан разрешить спуск в каталог 'core'.
    """
    root = FilterNode(
        mode="allow",
        allow=["/core/README.md"],
    )
    eng = FilterEngine(root)
    assert eng.may_descend("core") is True
    assert eng.may_descend("docs") is False

def test_render_with_allow_specific_file(tmp_path: Path, monkeypatch):
    """
    Сквозной тест: при секции mode:allow + allow:/core/README.md
    файл попадает в рендер секции, «шум» — нет.
    """
    # ── файловая структура
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "README.md").write_text("# Hello from Core README\nBody\n", encoding="utf-8")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "note.md").write_text("noise", encoding="utf-8")

    # ── конфиг: одна секция all
    (tmp_path / "lg-cfg").mkdir()
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        "all:\n"
        "  extensions: ['.md']\n"
        "  code_fence: false\n"        # md-only → без fenced/маркеров
        "  filters:\n"
        "    mode: allow\n"
        "    allow: ['/core/README.md']\n",
        encoding="utf-8"
    )

    # ── запуск пайплайна (виртуальный контекст секции)
    monkeypatch.chdir(tmp_path)
    out = run_render("sec:all", RunOptions())

    # В чистом MD режиме путь файла не печатается — проверяем содержимое
    assert "Hello from Core README" in out
    assert "Body" in out
    assert "noise" not in out

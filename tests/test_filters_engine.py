from lg.filters.model import FilterNode
from lg.filters.engine import FilterEngine


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

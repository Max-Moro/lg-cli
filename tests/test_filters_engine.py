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

def test_path_based_keys_simple():
    """
    Тест базовой функциональности path-based ключей.
    Path-based ключ "src/main/kotlin" разворачивается в иерархию узлов.
    """
    root = FilterNode(
        mode="block",
        children={
            "src/main/kotlin": FilterNode(
                mode="allow",
                allow=["*.kt"],
            )
        },
    )
    eng = FilterEngine(root)

    # ✅ разрешённые пути (в src/main/kotlin)
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("src/main/kotlin/utils/helper.kt")

    # ❌ запрещённые пути (другие в src/main)
    assert not eng.includes("src/main/java/App.java")
    assert not eng.includes("src/main/resources/app.properties")

    # ❌ запрещённые пути (вне иерархии)
    assert not eng.includes("src/test/kotlin/AppTest.kt")

def test_path_based_keys_multiple():
    """
    Несколько path-based ключей в одном узле.
    """
    root = FilterNode(
        mode="allow",
        allow=["**"],
        children={
            "src/main/kotlin": FilterNode(
                mode="allow",
                allow=["*.kt"],
            ),
            "src/main/java": FilterNode(
                mode="allow",
                allow=["*.java"],
            ),
        },
    )
    eng = FilterEngine(root)

    # ✅ разрешённые пути
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("src/main/java/App.java")

    # ❌ запрещённые пути
    assert not eng.includes("src/main/kotlin/readme.md")
    assert not eng.includes("src/main/java/readme.txt")

def test_path_based_keys_with_simple_keys():
    """
    Path-based ключи сосуществуют с простыми ключами.
    """
    root = FilterNode(
        mode="block",
        children={
            "src": FilterNode(
                mode="allow",  # Используем allow для whitelist
                allow=["**/*.py"],
            ),
            "docs/api": FilterNode(
                mode="allow",
                allow=["*.md"],
            ),
        },
    )
    eng = FilterEngine(root)

    # ✅ через простой ключ "src"
    assert eng.includes("src/main.py")
    assert eng.includes("src/app/utils.py")

    # ✅ через path-based ключ "docs/api"
    assert eng.includes("docs/api/index.md")
    assert eng.includes("docs/api/endpoints.md")

    # ❌ логика простого ключа (whitelist - только .py)
    assert not eng.includes("src/readme.md")

    # ❌ логика path-based ключа (вне docs/api)
    assert not eng.includes("docs/guide/intro.md")

def test_path_based_conflict_with_explicit_hierarchy():
    """
    Конфликт: path-based ключ пересекается с явно определённой иерархией.
    """
    import pytest

    root = FilterNode(
        mode="block",
        children={
            "src": FilterNode(
                mode="block",
                children={
                    "main": FilterNode(
                        mode="block",
                        children={}
                    )
                }
            ),
            "src/main/kotlin": FilterNode(
                mode="allow",
                allow=["*.kt"],
            ),
        },
    )

    # Должна выброситься ошибка при создании FilterEngine
    with pytest.raises(RuntimeError, match="Filter path conflict"):
        FilterEngine(root)

def test_path_based_with_transparent_intermediate():
    """
    Промежуточные узлы, созданные для path-based ключа, прозрачны.
    Они наследуют mode от родителя и не имеют своих правил.
    """
    root = FilterNode(
        mode="block",
        children={
            "a/b/c": FilterNode(
                mode="allow",
                allow=["*.txt"],
            ),
        },
    )
    eng = FilterEngine(root)

    # ✅ путь проходит через прозрачные узлы
    assert eng.includes("a/b/c/file.txt")

    # ❌ промежуточные узлы наследуют mode от корня (block)
    # поэтому файлы в a или a/b без явного разрешения не пройдут
    assert not eng.includes("a/file.txt")
    assert not eng.includes("a/b/file.txt")

def test_path_based_normalization():
    """
    Path-based ключи нормализуются (strip "/", lowercase).
    """
    root = FilterNode(
        mode="block",
        children={
            "/SRC/MAIN/KOTLIN": FilterNode(
                mode="allow",
                allow=["*.kt"],
            ),
        },
    )
    eng = FilterEngine(root)

    # ✅ нормализованный путь работает с любым регистром
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("SRC/MAIN/KOTLIN/app.kt")
    assert eng.includes("Src/Main/Kotlin/app.kt")

def test_path_based_extends_simple_key_no_conflict():
    """
    Допустимый случай: path-based ключ расширяет простой ключ.

    Когда есть явный простой ключ "src/main" с детьми,
    и path-based ключ "src/main/kotlin/lg/intellij", который создает
    промежуточные узлы "kotlin" -> "lg" -> "intellij" внутри "src/main".

    Это НЕ конфликт, потому что:
    - В "src/main" нет явного дочернего узла "kotlin"
    - Path-based ключ может свободно создать эту иерархию

    Имитирует реальную конфигурацию IntelliJ плагина.
    """
    root = FilterNode(
        mode="allow",
        allow=["/src/main/"],
        children={
            "src/main": FilterNode(
                mode="allow",
                allow=["/resources/"],
                children={
                    "resources": FilterNode(
                        mode="allow",
                        allow=["/META-INF/plugin.xml"],
                    )
                }
            ),
            "src/main/kotlin/lg/intellij": FilterNode(
                mode="allow",
                allow=["*.kt"],
            ),
        },
    )

    # Не должно быть ошибки при создании FilterEngine
    eng = FilterEngine(root)

    # ✅ файлы в явно определённой иерархии работают
    assert eng.includes("src/main/resources/META-INF/plugin.xml")

    # ✅ файлы в path-based иерархии работают
    assert eng.includes("src/main/kotlin/lg/intellij/MyClass.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/MyService.kt")

    # ❌ файлы вне разрешённых путей не проходят
    assert not eng.includes("src/main/kotlin/other/OtherClass.kt")
    assert not eng.includes("src/main/java/App.java")

def test_path_based_multiple_extending_same_prefix():
    """
    Несколько path-based ключей расширяют общий префикс.

    Проблема:
    - "src/main/kotlin/lg/intellij" разрешает /services/generation/ и /services/vfs/
    - "src/main/kotlin/lg/intellij/services/ai" добавляет правила для /ai/

    Промежуточный узел "services", созданный вторым ключом, НЕ должен затирать
    разрешения первого ключа для /services/generation/ и /services/vfs/.

    Имитирует реальную проблему из конфигурации IntelliJ плагина.
    """
    root = FilterNode(
        mode="allow",
        allow=["/src/"],
        children={
            "src/main/kotlin/lg/intellij": FilterNode(
                mode="allow",
                allow=[
                    "/services/generation/LgGenerationService.kt",
                    "/services/vfs/LgVirtualFileService.kt",
                    "/ui/components/LgButton.kt",
                ],
            ),
            "src/main/kotlin/lg/intellij/services/ai": FilterNode(
                mode="allow",
                allow=["*.kt"],
            ),
        },
    )

    eng = FilterEngine(root)

    # ✅ файлы из первого path-based ключа ДОЛЖНЫ работать
    assert eng.includes("src/main/kotlin/lg/intellij/services/generation/LgGenerationService.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/vfs/LgVirtualFileService.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/ui/components/LgButton.kt")

    # ✅ файлы из второго path-based ключа ДОЛЖНЫ работать
    assert eng.includes("src/main/kotlin/lg/intellij/services/ai/ClipboardProvider.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/ai/base/BaseProvider.kt")

    # ❌ файлы вне разрешённых путей НЕ должны проходить
    assert not eng.includes("src/main/kotlin/lg/intellij/services/other/SomeService.kt")
    assert not eng.includes("src/main/kotlin/lg/intellij/actions/SomeAction.kt")

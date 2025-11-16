from pathlib import Path
from lg.filtering.filters import FilterEngine
from lg.filtering.model import FilterNode
from lg.engine import run_render
from lg.types import RunOptions

def _engine():
    # root default-allow, but block *.log
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
    Nested mode:allow works as a 'strict filter': child allow narrows the parent.
    """
    root = FilterNode(
        mode="allow",
        allow=["vscode-ext/"],  # allow only vscode-ext/ subtree
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

    # Allowed paths
    assert eng.includes("vscode-ext/src/extension.ts")
    assert eng.includes("vscode-ext/src/client/start.ts")
    assert eng.includes("vscode-ext/package.json")
    assert eng.includes("vscode-ext/tsconfig.json")

    # Not listed in child allow - forbidden
    assert not eng.includes("vscode-ext/node_modules/lodash/index.js")
    assert not eng.includes("vscode-ext/README.md")
    assert not eng.includes("vscode-ext/yarn.lock")

    # Outside of root allow - forbidden
    assert not eng.includes("somewhere_else/file.ts")

def test_may_descend_allow_specific_file():
    """
    Regression: if allow specifies a specific file (/core/README.md),
    the pruner must allow descent into the 'core' directory.
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
    End-to-end test: with section mode:allow + allow:/core/README.md
    file is rendered in the section, 'noise' is not.
    """
    # file structure
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "README.md").write_text("# Hello from Core README\nBody\n", encoding="utf-8")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "note.md").write_text("noise", encoding="utf-8")

    # config: one section all
    (tmp_path / "lg-cfg").mkdir()
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        "all:\n"
        "  extensions: ['.md']\n"
        "  filters:\n"
        "    mode: allow\n"
        "    allow: ['/core/README.md']\n",
        encoding="utf-8"
    )

    # run pipeline (virtual section context)
    monkeypatch.chdir(tmp_path)
    out = run_render("sec:all", RunOptions())

    # In pure MD mode file path is not printed - check content
    assert "Hello from Core README" in out
    assert "Body" in out
    assert "noise" not in out

def test_path_based_keys_simple():
    """
    Test basic functionality of path-based keys.
    Path-based key "src/main/kotlin" is expanded into a node hierarchy.
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

    # Allowed paths (in src/main/kotlin)
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("src/main/kotlin/utils/helper.kt")

    # Forbidden paths (other in src/main)
    assert not eng.includes("src/main/java/App.java")
    assert not eng.includes("src/main/resources/app.properties")

    # Forbidden paths (outside hierarchy)
    assert not eng.includes("src/test/kotlin/AppTest.kt")

def test_path_based_keys_multiple():
    """
    Multiple path-based keys in one node.
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

    # Allowed paths
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("src/main/java/App.java")

    # Forbidden paths
    assert not eng.includes("src/main/kotlin/readme.md")
    assert not eng.includes("src/main/java/readme.txt")

def test_path_based_keys_with_simple_keys():
    """
    Path-based keys coexist with simple keys.
    """
    root = FilterNode(
        mode="block",
        children={
            "src": FilterNode(
                mode="allow",  # Use allow for whitelist
                allow=["**/*.py"],
            ),
            "docs/api": FilterNode(
                mode="allow",
                allow=["*.md"],
            ),
        },
    )
    eng = FilterEngine(root)

    # Through simple key "src"
    assert eng.includes("src/main.py")
    assert eng.includes("src/app/utils.py")

    # Through path-based key "docs/api"
    assert eng.includes("docs/api/index.md")
    assert eng.includes("docs/api/endpoints.md")

    # Logic of simple key (whitelist - .py only)
    assert not eng.includes("src/readme.md")

    # Logic of path-based key (outside docs/api)
    assert not eng.includes("docs/guide/intro.md")

def test_path_based_conflict_with_explicit_hierarchy():
    """
    Conflict: path-based key overlaps with explicitly defined hierarchy.
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

    # Error should be raised when creating FilterEngine
    with pytest.raises(RuntimeError, match="Filter path conflict"):
        FilterEngine(root)

def test_path_based_with_transparent_intermediate():
    """
    Intermediate nodes created for path-based keys are transparent.
    They inherit mode from parent and have no own rules.
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

    # Path passes through transparent nodes
    assert eng.includes("a/b/c/file.txt")

    # Intermediate nodes inherit mode from root (block)
    # so files in a or a/b without explicit permission won't pass
    assert not eng.includes("a/file.txt")
    assert not eng.includes("a/b/file.txt")

def test_path_based_normalization():
    """
    Path-based keys are normalized (strip "/", lowercase).
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

    # Normalized path works with any case
    assert eng.includes("src/main/kotlin/app.kt")
    assert eng.includes("SRC/MAIN/KOTLIN/app.kt")
    assert eng.includes("Src/Main/Kotlin/app.kt")

def test_path_based_extends_simple_key_no_conflict():
    """
    Allowed case: path-based key extends simple key.

    When there is an explicit simple key "src/main" with children,
    and a path-based key "src/main/kotlin/lg/intellij", which creates
    intermediate nodes "kotlin" -> "lg" -> "intellij" inside "src/main".

    This is NOT a conflict because:
    - "src/main" has no explicit child node "kotlin"
    - Path-based key can freely create this hierarchy

    Mimics real IntelliJ plugin configuration.
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

    # No error should occur when creating FilterEngine
    eng = FilterEngine(root)

    # Files in explicitly defined hierarchy work
    assert eng.includes("src/main/resources/META-INF/plugin.xml")

    # Files in path-based hierarchy work
    assert eng.includes("src/main/kotlin/lg/intellij/MyClass.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/MyService.kt")

    # Files outside allowed paths don't pass
    assert not eng.includes("src/main/kotlin/other/OtherClass.kt")
    assert not eng.includes("src/main/java/App.java")

def test_path_based_multiple_extending_same_prefix():
    """
    Multiple path-based keys extend a common prefix.

    Problem:
    - "src/main/kotlin/lg/intellij" allows /services/generation/ and /services/vfs/
    - "src/main/kotlin/lg/intellij/services/ai" adds rules for /ai/

    Intermediate node "services" created by the second key MUST NOT overwrite
    permissions of the first key for /services/generation/ and /services/vfs/.

    Mimics real problem from IntelliJ plugin configuration.
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

    # Files from first path-based key MUST work
    assert eng.includes("src/main/kotlin/lg/intellij/services/generation/LgGenerationService.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/vfs/LgVirtualFileService.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/ui/components/LgButton.kt")

    # Files from second path-based key MUST work
    assert eng.includes("src/main/kotlin/lg/intellij/services/ai/ClipboardProvider.kt")
    assert eng.includes("src/main/kotlin/lg/intellij/services/ai/base/BaseProvider.kt")

    # Files outside allowed paths MUST NOT pass
    assert not eng.includes("src/main/kotlin/lg/intellij/services/other/SomeService.kt")
    assert not eng.includes("src/main/kotlin/lg/intellij/actions/SomeAction.kt")

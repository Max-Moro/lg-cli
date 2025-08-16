from pathlib import Path
from .conftest import run_cli

def test_code_fence_on_and_off(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # создаём простой .py-файл в корне проекта
    p = tmpproj / "m.py"
    p.write_text("print('x')\n", encoding="utf-8")

    # 1) fencing включён (в секции all code_fence: true) → должен быть блок ```python
    cp1 = run_cli(tmpproj, "render", "sec:all")
    assert cp1.returncode == 0, cp1.stderr
    out1 = cp1.stdout
    assert "```python" in out1
    # в fenced-блоке мы всегда печатаем маркер файла
    assert "# —— FILE: m.py ——" in out1

    # 2) fencing принудительно выключаем флагом CLI → ``` отсутствует, маркер остаётся
    cp2 = run_cli(tmpproj, "render", "sec:all", "--no-fence")
    assert cp2.returncode == 0, cp2.stderr
    out2 = cp2.stdout
    assert "```python" not in out2
    assert "# —— FILE: m.py ——" in out2

def test_md_only_without_fence_no_markers(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # файл документации
    (tmpproj / "README.md").write_text("# Title\nBody\n", encoding="utf-8")

    # секция docs в фикстуре tmpproj имеет code_fence: false и только .md
    cp = run_cli(tmpproj, "render", "sec:docs")
    assert cp.returncode == 0, cp.stderr
    out = cp.stdout
    assert "```" not in out                 # fencing не используется
    assert "# —— FILE:" not in out          # для md-only маркеров нет
    assert "Body" in out

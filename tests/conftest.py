import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from lg.adapters.context import LightweightContext
from lg.stats import TokenService

# Импорт из унифицированной инфраструктуры
from tests.infrastructure.file_utils import write
from tests.infrastructure.testing_utils import TokenServiceStub, stub_tokenizer


@pytest.fixture
def tmpproj(tmp_path: Path):
    """Минимальный проект под схему: lg-cfg/sections.yaml + ctx/tpl в корне lg-cfg/."""
    root = tmp_path
    # sections.yaml с двумя секциями
    write(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent("""
        all:
          extensions: [".md", ".py"]
          code_fence: true
          markdown:
            max_heading_level: 2
          targets:
            - match: "/pkg/**.py"
              python:
                strip_function_bodies: true
        docs:
          extensions: [".md"]
          code_fence: false
          markdown:
            max_heading_level: 3
          targets:
            - match: ["/docs/**.md"]
        """).strip() + "\n",
    )
    # шаблон и два контекста
    write(root / "lg-cfg" / "a.tpl.md", "Intro\n\n${docs}\n")
    write(root / "lg-cfg" / "a.ctx.md", "Intro (ctx)\n\n${docs}\n")
    write(root / "lg-cfg" / "b.ctx.md", "X ${tpl:a} Y ${all}\n")
    return root

@pytest.fixture(autouse=True)
def _allow_migrations_without_git(monkeypatch):
    # безопасно для юнит-тестов: в проде переменная не задана
    monkeypatch.setenv("LG_MIGRATE_ALLOW_NO_GIT", "1")

def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )

def lctx(
        raw_text: str = "# Test content",
        filename: str = "test.py",
        group_size: int = 1,
        mixed: bool = False
) -> LightweightContext:
    """
    Создает stub LightweightContext для тестов.

    Args:
        raw_text: Содержимое файла
        filename: Имя файла
        group_size: Размер группы
        mixed: Смешанные языки

    Returns:
        LightweightContext для использования в тестах
    """
    test_path = Path(filename)
    return LightweightContext(
        file_path=test_path,
        raw_text=raw_text,
        group_size=group_size,
        mixed=mixed
    )


def lctx_py(raw_text: str = "# Test Python", group_size: int = 1, mixed: bool = False) -> LightweightContext:
    """Создает LightweightContext для Python файла."""
    return lctx(raw_text=raw_text, filename="test.py", group_size=group_size, mixed=mixed)


def lctx_ts(raw_text: str = "// Test TypeScript", group_size: int = 1, mixed: bool = False) -> LightweightContext:
    """Создает LightweightContext для TypeScript файла.""" 
    return lctx(raw_text=raw_text, filename="test.ts", group_size=group_size, mixed=mixed)


def lctx_md(raw_text: str = "# Test Markdown", group_size: int = 1, mixed: bool = False) -> LightweightContext:
    """Создает LightweightContext для Markdown файла."""
    return lctx(raw_text=raw_text, filename="test.md", group_size=group_size, mixed=mixed)


def jload(s: str):
    return json.loads(s)

# ==== Заглушки для энкодинга токенов ====
# Перенесены в tests.infrastructure.testing_utils

# Экспортируем хелперы для использования в других тестах
__all__ = ["lctx", "lctx_py", "lctx_ts", "lctx_md", "run_cli", "jload", "stub_tokenizer"]
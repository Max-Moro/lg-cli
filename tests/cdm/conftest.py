from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# Импорт из унифицированной инфраструктуры  
from tests.infrastructure import write
from tests.infrastructure import make_run_context as mk_run_ctx

def _root_sections_yaml() -> str:
    # Корневой конфиг: хотя бы одна простая секция, но тесты CDM опираются на child-секции
    return textwrap.dedent("""
    root-md:
      extensions: [".md"]
      filters:
        mode: allow
        allow:
          - "/docs/**"
    """).strip() + "\n"


def _svc_a_sections() -> str:
    # Секция 'a' со скоупом packages/svc-a
    return textwrap.dedent("""
    a:
      extensions: [".py", ".md"]
      filters:
        mode: allow
        allow:
          - "/src/**"
          - "/README.md"
      targets:
        - match: "/src/pkg/**.py"
          python:
            strip_function_bodies: true
    """).strip() + "\n"


def _web_sections() -> str:
    # Секция 'web-api' в apps/web
    return textwrap.dedent("""
    web-api:
      extensions: [".md"]
      filters:
        mode: allow
        allow:
          - "/docs/**"
    """).strip() + "\n"


@pytest.fixture
def monorepo(tmp_path: Path) -> Path:
    """
    Строит монорепу:
      repo/
        lg-cfg/
          sections.yaml
          a.ctx.md     (использует tpl:local-intro и адресные секции)
          local-intro.tpl.md (вставляет секцию @packages/svc-a:a один раз)
        packages/svc-a/lg-cfg/
          a.sec.yaml
          docs/guide.tpl.md
        apps/web/lg-cfg/
          web.sec.yaml
          docs/guide.tpl.md
      и немного исходников под фильтры
    """
    root = tmp_path

    # --- root lg-cfg ---
    write(root / "lg-cfg" / "sections.yaml", _root_sections_yaml())
    write(root / "lg-cfg" / "local-intro.tpl.md", "Intro from ROOT tpl\n\n${@packages/svc-a:a}\n")
    write(
        root / "lg-cfg" / "a.ctx.md",
        textwrap.dedent("""
        # Root Context A

        ${tpl:local-intro}

        ## Include child section A again
        ${@packages/svc-a:a}

        ## Include a child template (no extra sections inside to keep multiplicity=2)
        ${tpl@apps/web:docs/guide}

        ## And include a child section from apps/web
        ${@apps/web:web-api}
        """).strip() + "\n"
    )

    # --- child: packages/svc-a ---
    write(root / "packages" / "svc-a" / "lg-cfg" / "a.sec.yaml", _svc_a_sections())
    write(root / "packages" / "svc-a" / "lg-cfg" / "docs" / "guide.tpl.md", "SVC-A GUIDE (no sections here)\n")

    # --- child: apps/web ---
    write(root / "apps" / "web" / "lg-cfg" / "web.sec.yaml", _web_sections())
    write(root / "apps" / "web" / "lg-cfg" / "docs" / "guide.tpl.md", "WEB GUIDE (no sections here)\n")
    # Доп. контекст в child для проверки ctx@...
    write(root / "apps" / "web" / "lg-cfg" / "external.ctx.md", "# WEBCTX\n\n${web-api}\n")
    # И корневой контекст, который вставляет child-контекст
    write(root / "lg-cfg" / "x.ctx.md", "# ROOT X\n\n${ctx@apps/web:external}\n")

    # --- payload files for filters/targets ---
    write(root / "packages" / "svc-a" / "src" / "pkg" / "x.py", "def foo():\n    return 1\n")
    write(root / "packages" / "svc-a" / "src" / "other" / "y.py", "print('ok')\n")
    write(root / "packages" / "svc-a" / "README.md", "# svc-a\n")
    write(root / "apps" / "web" / "docs" / "index.md", "# web docs\n")

    return root

__all__ = ["mk_run_ctx"]

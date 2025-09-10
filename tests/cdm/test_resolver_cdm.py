from __future__ import annotations

from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.context.resolver import resolve_context
from lg.run_context import RunContext
from lg.tokens.service import TokenService
from lg.types import RunOptions
from lg.vcs import NullVcs

from tests.conftest import write


def _mk_run_ctx(root: Path) -> RunContext:
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    return RunContext(root=root, options=RunOptions(), cache=cache, vcs=NullVcs(), token_service=TokenService())


def test_resolve_context_collects_addressed_sections_and_multiplicity(monorepo: Path):
    """
    В root a.ctx.md:
      - ${tpl:local-intro}       → включает @packages/svc-a:a один раз
      - ${@packages/svc-a:a}     → второй раз
      - ${tpl@apps/web:docs/guide} → нет секций внутри
      - ${@apps/web:web-api}     → одна секция из apps/web
    Ожидаем:
      - два CanonSectionId: 'packages/svc-a::a' с multiplicity=2 и 'apps/web::web-api' с multiplicity=1
      - ph2canon маппит сырые плейсхолдеры на эти каноны
    """
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:a", rc)
    assert spec.kind == "context" and spec.name == "a"

    # Свернём multiplicity по canon.as_key()
    mult = {}
    for r in spec.section_refs:
        mult[r.canon.as_key()] = mult.get(r.canon.as_key(), 0) + r.multiplicity

    assert mult.get("packages/svc-a::a") == 2
    assert mult.get("apps/web::web-api") == 1

    # ph2canon должен содержать ключи исходных плейсхолдеров
    assert "@packages/svc-a:a" in spec.ph2canon
    assert "@apps/web:web-api" in spec.ph2canon
    assert spec.ph2canon["@packages/svc-a:a"].as_key() == "packages/svc-a::a"
    assert spec.ph2canon["@apps/web:web-api"].as_key() == "apps/web::web-api"


def test_resolve_sec_virtual_context_uses_root_scope(monorepo: Path):
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("sec:a", rc)
    assert spec.kind == "section" and spec.name == "a"
    # Корневой lg-cfg → scope_rel == ""
    assert spec.section_refs and spec.section_refs[0].canon.scope_rel == ""


def test_template_cycle_is_detected(monorepo: Path):
    """
    Создаём цикл в tpl между apps/web и packages/svc-a и включаем его из root ctx.
    """
    write(
        monorepo / "packages" / "svc-a" / "lg-cfg" / "docs" / "loop.tpl.md",
        "${tpl@apps/web:docs/loop}\n",
    )
    write(
        monorepo / "apps" / "web" / "lg-cfg" / "docs" / "loop.tpl.md",
        "${tpl@packages/svc-a:docs/loop}\n",
    )
    # Перезаписываем корневой контекст, чтобы точно попасть в цикл
    write(
        monorepo / "lg-cfg" / "a.ctx.md",
        "${tpl@apps/web:docs/loop}\n",
    )

    rc = _mk_run_ctx(monorepo)
    with pytest.raises(RuntimeError, match="TPL cycle detected"):
        resolve_context("ctx:a", rc)

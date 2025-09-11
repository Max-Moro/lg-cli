from __future__ import annotations

from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.context.resolver import resolve_context
from lg.manifest.builder import build_manifest
from lg.plan.planner import build_plan
from lg.render.sections import render_by_section
from lg.run_context import RunContext
from lg.stats import TokenService
from lg.types import RunOptions
from lg.vcs import NullVcs


def _mk_run_ctx(root: Path) -> RunContext:
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    return RunContext(root=root, options=RunOptions(), cache=cache, vcs=NullVcs(), tokenizer=TokenService())


def test_planner_and_render_for_addressed_sections(monorepo: Path):
    """
    Проверяем:
      • для секции packages/svc-a::a — use_fence=True, есть группы python и '' (md),
        рендер содержит ```python и FILE-маркер с укороченной меткой README.md
      • для секции apps/web::web-api — md_only=True, use_fence=False, рендер без FILE-маркеров
    """
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:a", rc)

    manifest = build_manifest(root=monorepo, spec=spec, mode=rc.options.mode, vcs=rc.vcs)
    plan = build_plan(manifest, rc)

    # Быстрый smoke: есть обе секции
    ids = [sec.section_id.as_key() for sec in plan.sections]
    assert "packages/svc-a::a" in ids
    assert "apps/web::web-api" in ids

    # Проверим свойства плана
    sec_a = next(s for s in plan.sections if s.section_id.as_key() == "packages/svc-a::a")
    assert sec_a.use_fence is True and sec_a.md_only is False
    langs = {g.lang for g in sec_a.groups}
    assert "python" in langs and "" in langs  # есть и код, и markdown-группа

    # Секция web-api — чистый MD без fenced/FILE
    sec_web = next(s for s in plan.sections if s.section_id.as_key() == "apps/web::web-api")
    assert sec_web.md_only is True and sec_web.use_fence is False

    # Рендер
    from lg.adapters.engine import process_groups
    blobs = process_groups(plan, rc)
    rendered_by_sec = render_by_section(plan, blobs)

    txt_a = rendered_by_sec[sec_a.section_id]
    assert "```python" in txt_a
    # метка README должна быть короткой (auto снимает общий префикс)
    assert "# —— FILE: README.md ——" in txt_a or "# —— FILE: packages/svc-a/README.md ——" in txt_a
    # возможно, для md-группы тоже fenced-блок без языка
    assert "```" in txt_a

    txt_web = rendered_by_sec[sec_web.section_id]
    assert "# —— FILE:" not in txt_web
    assert "```" not in txt_web
    assert "# web docs" in txt_web  # содержимое apps/web/docs/index.md

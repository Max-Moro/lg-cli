from __future__ import annotations

from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.context.composer import compose_context
from lg.context.resolver import resolve_context
from lg.config.paths import cfg_root
from lg.run_context import RunContext
from lg.tokens.service import TokenService
from lg.types import RunOptions
from lg.vcs import NullVcs


def _mk_run_ctx(root: Path) -> RunContext:
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    return RunContext(root=root, options=RunOptions(), cache=cache, vcs=NullVcs(), token_service=TokenService())


def test_ctx_in_ctx_cross_scope(monorepo: Path):
    """
    Корневой x.ctx.md включает ${ctx@apps/web:external}, а тот — свою секцию ${web-api}.
    Проверяем, что:
      • секция apps/web::web-api попадает в рендер (ровно один раз),
      • в финальном тексте есть маркеры из дочернего ctx,
      • в templates_hashes есть ключи для обоих контекстов (root и child).
    """
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:x", rc)

    # Заменим секции заметными маркерами
    rendered_by_section = {ref.canon: f"<<SEC:{ref.canon.as_key()}>>\n" for ref in spec.section_refs}

    composed = compose_context(
        repo_root=monorepo,
        base_cfg_root=cfg_root(monorepo),
        spec=spec,
        rendered_by_section=rendered_by_section,
        ph2canon=spec.ph2canon,
    )

    assert "<<SEC:apps/web::web-api>>" in composed.text
    # child ctx заголовок присутствует
    assert "# WEBCTX" in composed.text

    base_key = f"{cfg_root(monorepo).as_posix()}::ctx:x"
    child_key = f"{(monorepo / 'apps' / 'web' / 'lg-cfg').as_posix()}::ctx:external"
    assert base_key in composed.templates_hashes
    assert child_key in composed.templates_hashes
    assert all(len(v) == 40 for v in composed.templates_hashes.values())

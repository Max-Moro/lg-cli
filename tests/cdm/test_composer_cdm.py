from __future__ import annotations

from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.config.paths import cfg_root
from lg.context.composer import compose_context
from lg.context.resolver import resolve_context
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.vcs import NullVcs


def _mk_run_ctx(root: Path) -> RunContext:
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    return RunContext(root=root, options=RunOptions(), cache=cache, vcs=NullVcs(), tokenizer=default_tokenizer())


def test_compose_context_expands_tpl_at_and_builds_hashes(monorepo: Path):
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:a", rc)

    # Синтетический рендер секций: подставим заметные маркеры
    rendered_by_section = {}
    for ref in spec.section_refs:
        rendered_by_section[ref.canon] = f"<<SEC:{ref.canon.as_key()}>>\n"

    composed = compose_context(
        repo_root=monorepo,
        base_cfg_root=cfg_root(monorepo),
        spec=spec,
        rendered_by_section=rendered_by_section,
        ph2canon=spec.ph2canon,
    )

    # В финальном тексте должен быть развёрнутый child-шаблон
    assert "WEB GUIDE" in composed.text
    # И два вхождения секции packages/svc-a::a
    assert composed.text.count("<<SEC:packages/svc-a::a>>") == 2

    # sections_only_text — без "WEB GUIDE", только секции
    assert "WEB GUIDE" not in composed.sections_only_text
    assert composed.sections_only_text.count("<<SEC:packages/svc-a::a>>") == 2

    # Хэши шаблонов: ключи вида "<cfg_root>::ctx:a" и "<apps/web/lg-cfg>::docs/guide"
    base_key = f"{cfg_root(monorepo).as_posix()}::ctx:a"
    child_key = f"{(monorepo / 'apps' / 'web' / 'lg-cfg').as_posix()}::tpl:docs/guide"
    assert base_key in composed.templates_hashes
    assert child_key in composed.templates_hashes
    assert all(len(v) == 40 for v in composed.templates_hashes.values())  # sha1


def test_compose_context_fails_on_unknown_section_placeholder(monorepo: Path):
    # Возьмём реальный spec, но дадим пустую карту ph2canon, чтобы спровоцировать ошибку
    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:a", rc)

    with pytest.raises(RuntimeError, match="Unknown section placeholder"):
        compose_context(
            repo_root=monorepo,
            base_cfg_root=cfg_root(monorepo),
            spec=spec,
            rendered_by_section={},     # не важно, упадём раньше
            ph2canon={},                # ломаем инвариант намеренно
        )

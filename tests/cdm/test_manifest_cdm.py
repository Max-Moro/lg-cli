from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from lg.cache.fs_cache import Cache
from lg.context.resolver import resolve_context
from lg.manifest.builder import build_manifest
from lg.run_context import RunContext
from lg.types import RunOptions
from lg.vcs import VcsProvider
from tests.conftest import write


def _mk_run_ctx(root: Path) -> RunContext:
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    # VCS нам не нужен здесь — передадим явно в build_manifest, где требуется
    class _NullVcs:
        def changed_files(self, root: Path):  # type: ignore[override]
            return set()
    return RunContext(root=root, options=RunOptions(), cache=cache, vcs=_NullVcs())  # type: ignore[arg-type]


class FakeVcs(VcsProvider):
    def __init__(self, changed: set[str]) -> None:
        self._changed = set(changed)
    def changed_files(self, root: Path) -> set[str]:
        return set(self._changed)


def _manifest_for_ctx(root: Path, ctx_name: str, *, mode: str = "all", vcs=None):
    rc = _mk_run_ctx(root)
    spec = resolve_context(f"ctx:{ctx_name}", rc)
    return build_manifest(root=root, spec=spec, mode=mode, vcs=vcs)


def test_scope_and_filters_limit_to_scope(monorepo: Path):
    """
    Секция packages/svc-a::a должна видеть только свой скоуп (packages/svc-a/**) и
    пропускать файлы по allow:
      - /src/**, /README.md
    Ничего из apps/web/** попадать не должно.
    """
    man = _manifest_for_ctx(monorepo, "a")

    # найдём секцию 'packages/svc-a::a'
    sec = next(s for s in man.iter_sections() if s.id.as_key() == "packages/svc-a::a")
    rels = [f.rel_path for f in sec.files]

    # Попали файлы из своего скоупа и по allow
    assert "packages/svc-a/src/pkg/x.py" in rels
    assert "packages/svc-a/src/other/y.py" in rels
    assert "packages/svc-a/README.md" in rels

    # Не попали ничего из другого скоупа
    assert all(not p.startswith("apps/web/") for p in rels)


def test_targets_match_are_relative_to_scope(monorepo: Path):
    """
    В a.sec.yaml есть targets.match: '/src/pkg/**.py' → должен примениться только к
    packages/svc-a/src/pkg/x.py, но не к src/other/y.py.
    """
    man = _manifest_for_ctx(monorepo, "a")
    sec = next(s for s in man.iter_sections() if s.id.as_key() == "packages/svc-a::a")

    # карта rel -> overrides для python
    overrides = {
        f.rel_path: (f.adapter_overrides.get("python") or {})
        for f in sec.files
    }

    assert overrides.get("packages/svc-a/src/pkg/x.py").get("strip_function_bodies") is True
    assert "python" not in sec.files[[f.rel_path for f in sec.files].index("packages/svc-a/src/other/y.py")].adapter_overrides


def test_changes_mode_filters_by_vcs_and_scope(monorepo: Path):
    """
    В changes-режиме должны попасть только изменённые файлы И при этом в пределах скоупа.
    """
    changed = {
        "packages/svc-a/src/only_this.py",      # попадёт (создадим файл)
        "apps/web/docs/index.md",               # другой скоуп — не в эту секцию
        "packages/svc-a/README.md",             # попадёт, если изменён
    }

    # создадим отсутствующий файл из changed
    write(monorepo / "packages" / "svc-a" / "src" / "only_this.py", "print('changed')\n")

    man = _manifest_for_ctx(monorepo, "a", mode="changes", vcs=FakeVcs(changed))

    sec = next(s for s in man.iter_sections() if s.id.as_key() == "packages/svc-a::a")
    rels = [f.rel_path for f in sec.files]

    assert "packages/svc-a/src/only_this.py" in rels
    assert "packages/svc-a/README.md" in rels
    # index.md из apps/web изменён, но другой скоуп → не появится в этой секции
    assert "apps/web/docs/index.md" not in rels


def test_empty_policy_include_allows_empty_files(monorepo: Path):
    """
    Если в секции указать python.empty_policy: include, пустой .py не отфильтруется.
    """
    # 1) Внесём empty_policy внутрь секции a → под адаптер python
    sec_path = monorepo / "packages" / "svc-a" / "lg-cfg" / "a.sec.yaml"
    y = YAML()
    data = y.load(sec_path.read_text(encoding="utf-8")) or {}
    a = data.setdefault("a", {})
    py = a.setdefault("python", {})
    py["empty_policy"] = "include"
    # перезаписываем YAML (чтобы сохранить читаемый вид)
    buf = io.StringIO()
    y.dump(data, buf)
    sec_path.write_text(buf.getvalue(), encoding="utf-8")

    # 2) Создаём пустой файл в allow-зоне
    empty_fp = monorepo / "packages" / "svc-a" / "src" / "pkg" / "empty.py"
    empty_fp.parent.mkdir(parents=True, exist_ok=True)
    empty_fp.write_bytes(b"")

    # 3) Строим манифест и проверяем попадание пустого файла
    man = _manifest_for_ctx(monorepo, "a")
    sec = next(s for s in man.iter_sections() if s.id.as_key() == "packages/svc-a::a")
    rels = [f.rel_path for f in sec.files]
    assert "packages/svc-a/src/pkg/empty.py" in rels


def test_missing_sections_diagnostic_includes_available(monorepo: Path):
    """
    Если в контексте запрошена несуществующая секция в child, build_manifest должен
    упасть с сообщением:
      - указывает scope: apps/web/...
      - перечисляет плейсхолдер и доступные секции в этом скоупе
    """
    # создадим контекст, который ссылается на несуществующую секцию в apps/web
    bad_ctx = monorepo / "lg-cfg" / "bad.ctx.md"
    bad_ctx.write_text("${@apps/web:missing}\n", encoding="utf-8")

    rc = _mk_run_ctx(monorepo)
    spec = resolve_context("ctx:bad", rc)

    with pytest.raises(RuntimeError) as ei:
        build_manifest(root=monorepo, spec=spec, mode="all")

    msg = str(ei.value)
    assert "Section(s) not found" in msg
    assert "scope: " in msg and "apps/web" in msg
    assert "available:" in msg
    # в нашем фикстурном apps/web есть 'web-api'
    assert "web-api" in msg
    # и должен присутствовать исходный плейсхолдер
    assert "placeholder '@apps/web:missing'" in msg

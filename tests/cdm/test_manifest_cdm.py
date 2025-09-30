from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from lg.io.manifest import build_section_manifest
from lg.config import load_config
from lg.template.context import TemplateContext
from lg.types import SectionRef
from lg.vcs import VcsProvider
from tests.infrastructure.file_utils import write
from .conftest import mk_run_ctx


class FakeVcs(VcsProvider):
    def __init__(self, changed: set[str]) -> None:
        self._changed = set(changed)
    def changed_files(self, root: Path) -> set[str]:
        return set(self._changed)


def _build_section_manifest(
    root: Path, 
    section_name: str, 
    scope_rel: str = "", 
    *, 
    vcs_mode: str = "all", 
    vcs=None
):
    """
    Хелпер для построения манифеста одной секции в новом пайплайне V2.
    
    Args:
        root: Корень репозитория
        section_name: Имя секции
        scope_rel: Относительный путь к скоупу (пустой для корня)
        vcs_mode: Режим VCS ("all" или "changes")
        vcs: VCS провайдер
        
    Returns:
        SectionManifest для указанной секции
    """
    rc = mk_run_ctx(root)
    template_ctx = TemplateContext(rc)
    
    # Определяем scope_dir на основе scope_rel
    if scope_rel:
        scope_dir = (root / scope_rel).resolve()
    else:
        scope_dir = root
    
    section_ref = SectionRef(
        name=section_name,
        scope_rel=scope_rel,
        scope_dir=scope_dir
    )
    
    config = load_config(scope_dir)
    section_cfg = config.sections.get(section_ref.name)
    
    if not section_cfg:
        available = list(config.sections.keys())
        raise RuntimeError(
            f"Section '{section_ref.name}' not found in {scope_dir}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )
    
    return build_section_manifest(
        section_ref=section_ref,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=root,
        vcs=vcs or rc.vcs,
        vcs_mode=vcs_mode
    )

def test_scope_and_filters_limit_to_scope(monorepo: Path):
    """
    Секция packages/svc-a::a должна видеть только свой скоуп (packages/svc-a/**) и
    пропускать файлы по allow:
      - /src/**, /README.md
    Ничего из apps/web/** попадать не должно.
    """
    # Тестируем секцию 'a' из скоупа 'packages/svc-a'
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")
    rels = [f.rel_path for f in manifest.files]

    # Попали файлы из своего скоупа и по allow
    assert "packages/svc-a/src/pkg/x.py" in rels
    assert "packages/svc-a/src/other/y.py" in rels
    assert "packages/svc-a/README.md" in rels

    # Не попали ничего из другого скоупа
    assert all(not p.startswith("apps/web/") for p in rels)
    
    # Проверяем, что секция правильно определила свой скоуп
    assert manifest.ref.scope_rel == "packages/svc-a"
    assert manifest.ref.name == "a"


def test_targets_match_are_relative_to_scope(monorepo: Path):
    """
    В a.sec.yaml есть targets.match: '/src/pkg/**.py' → должен примениться только к
    packages/svc-a/src/pkg/x.py, но не к src/other/y.py.
    """
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")

    # карта rel -> overrides для python
    overrides = {
        f.rel_path: (f.adapter_overrides.get("python") or {})
        for f in manifest.files
    }

    assert overrides.get("packages/svc-a/src/pkg/x.py").get("strip_function_bodies") is True
    
    # Найдем файл src/other/y.py
    other_file = next((f for f in manifest.files if f.rel_path == "packages/svc-a/src/other/y.py"), None)
    assert other_file is not None
    assert "python" not in other_file.adapter_overrides


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

    manifest = _build_section_manifest(
        monorepo, "a", "packages/svc-a", 
        vcs_mode="changes", 
        vcs=FakeVcs(changed)
    )
    rels = [f.rel_path for f in manifest.files]

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
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")
    rels = [f.rel_path for f in manifest.files]
    assert "packages/svc-a/src/pkg/empty.py" in rels


def test_missing_sections_diagnostic_includes_available(monorepo: Path):
    """
    Если запрошена несуществующая секция в child скоупе, build_section_manifest должен
    упасть с сообщением:
      - указывает scope: apps/web/...
      - перечисляет доступные секции в этом скоупе
    """
    # Тестируем попытку получить несуществующую секцию 'missing' из скоупа 'apps/web'
    with pytest.raises(RuntimeError) as ei:
        _build_section_manifest(monorepo, "missing", "apps/web")

    msg = str(ei.value)
    assert "not found" in msg
    assert "apps" in msg and "web" in msg
    assert "Available:" in msg
    # в нашем фикстурном apps/web есть 'web-api'
    assert "web-api" in msg

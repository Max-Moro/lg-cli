from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List
from typing import Tuple

# Ресурсы лежат под пакетом lg._skeletons/<preset>/lg-cfg/...
_SKELETONS_PKG = "lg._skeletons"


def list_presets() -> List[str]:
    """Перечислить доступные пресеты, основываясь на подпапках внутри lg/_skeletons/."""
    try:
        base = resources.files(_SKELETONS_PKG)
    except Exception:
        return []
    out: List[str] = []
    for entry in base.iterdir():
        try:
            if entry.is_dir():
                out.append(entry.name)
        except Exception:
            continue
    out.sort()
    return out


def _iter_all_files(node):
    """Рекурсивный обход Traversable-ресурсов (совместимо с .whl/zip)."""
    for entry in node.iterdir():
        if entry.is_dir():
            yield from _iter_all_files(entry)
        elif entry.is_file():
            yield entry


def _collect_skeleton_entries(preset: str) -> List[Tuple[str, bytes]]:
    """
    Собирает пары (rel, data) для всех файлов из пресета.
    Структура пресета: <preset>/lg-cfg/**/*
    """
    base = resources.files(_SKELETONS_PKG) / preset
    if not base.exists():
        raise RuntimeError(f"Preset not found: {preset}")
    root = base / "lg-cfg"
    if not root.exists():
        raise RuntimeError(f"Preset '{preset}' has no 'lg-cfg' directory")
    out: List[Tuple[str, bytes]] = []
    for res in _iter_all_files(root):
        rel = res.relative_to(root).as_posix()
        try:
            data = res.read_bytes()
        except Exception:
            # На некоторых платформах read_bytes может отсутствовать — fallback через open()
            with res.open("rb") as f:
                data = f.read()
        out.append((rel, data))
    out.sort(key=lambda t: t[0])
    return out


def _want_file(rel: str, *, include_examples: bool, include_models: bool) -> bool:
    # rel — путь относительно lg-cfg/, POSIX
    if not include_examples and (rel.endswith(".tpl.md") or rel.endswith(".ctx.md")):
        return False
    if not include_models and rel == "models.yaml":
        return False
    return True


def init_cfg(
    *,
    repo_root: Path,
    preset: str = "basic",
    force: bool = False,
    include_examples: bool = True,
    include_models: bool = False,
    dry_run: bool = False,
) -> Dict:
    """
    Разворачивает пресет в <repo_root>/lg-cfg/.
    Возвращает JSON-совместимый словарь с полями: ok, created, skipped, conflicts, preset.
    """
    repo_root = repo_root.resolve()
    target = (repo_root / "lg-cfg").resolve()

    # Составим план копирования
    created: List[str] = []
    skipped: List[str] = []
    conflicts: List[str] = []
    plan: List[Tuple[str, bytes]] = []

    # Собираем исходные файлы пресета
    try:
        src_entries = _collect_skeleton_entries(preset)
    except Exception as e:
        return {"ok": False, "error": str(e), "preset": preset}

    for rel, data in src_entries:
        if not _want_file(rel, include_examples=include_examples, include_models=include_models):
            skipped.append(rel)
            continue
        dst = target / rel
        if dst.exists() and not force:
            conflicts.append(rel)
            continue
        plan.append((rel, data))

    # Если есть конфликты и не force — выходим/сообщаем
    if conflicts and not force:
        return {
            "ok": False,
            "preset": preset,
            "created": [],
            "skipped": skipped,
            "conflicts": sorted(conflicts),
            "message": "Use --force to overwrite existing files.",
        }

    # dry-run: покажем что будет создано/перезаписано и выйдем
    if dry_run:
        will_create: List[str] = []
        will_overwrite: List[str] = []
        for rel, _ in plan:
            dst = (target / rel)
            if dst.exists():
                will_overwrite.append(rel)
            else:
                will_create.append(rel)
        return {
            "ok": True,
            "preset": preset,
            "dryRun": True,
            "target": str(target),
            "willCreate": sorted(will_create),
            "willOverwrite": sorted(will_overwrite),
            "skipped": sorted(skipped),
        }

    # Выполняем запись
    for rel, data in plan:
        dst = (target / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            f.write(data)
        created.append(rel)

    return {
        "ok": True,
        "preset": preset,
        "target": str(target),
        "created": sorted(created),
        "skipped": sorted(skipped),
        "conflicts": sorted(conflicts) if force else [],
    }

# ---------------- CLI glue ---------------- #

def add_cli(subparsers) -> None:
    """
    Регистрирует подкоманду 'init' и привязывает обработчик через set_defaults(func=...).
    Это позволяет развивать CLI без правок в lg/cli.py.
    """
    sp = subparsers.add_parser(
        "init",
        help="Инициализировать стартовую конфигурацию lg-cfg/ из упакованных пресетов",
    )
    sp.add_argument("--preset", default="basic", help="имя пресета (см. --list-presets)")
    sp.add_argument("--force", action="store_true", help="перезаписывать существующие файлы")
    sp.add_argument("--no-examples", action="store_true", help="не копировать примеры *.tpl.md и *.ctx.md")
    sp.add_argument("--with-models", action="store_true", help="положить пример lg-cfg/models.yaml")
    sp.add_argument("--dry-run", action="store_true", help="показать план действий, ничего не изменяя на диске")
    sp.add_argument("--list-presets", action="store_true", help="перечислить доступные пресеты и выйти")
    # Хендлер — сюда придёт argparse.Namespace
    sp.set_defaults(func=_run_cli, cmd="init")


def _run_cli(ns) -> int:
    """Обработчик подкоманды `lg init`."""
    from .jsonic import dumps as jdumps
    if bool(getattr(ns, "list_presets", False)):
        print(jdumps({"presets": list_presets()}))
        return 0

    root = Path.cwd()
    result = init_cfg(
        repo_root=root,
        preset=str(ns.preset),
        force=bool(getattr(ns, "force", False)),
        include_examples=not bool(getattr(ns, "no_examples", False)),
        include_models=bool(getattr(ns, "with_models", False)),
        dry_run=bool(getattr(ns, "dry_run", False)),
    )
    # После успешной инициализации (и не dry-run) мягко приведём конфиг к актуальному виду
    if not bool(getattr(ns, "dry_run", False)) and result.get("ok"):
        try:
            from .config.paths import cfg_root as _cfg_root
            from .migrate import ensure_cfg_actual as _ensure
            _ensure(_cfg_root(root))
        except Exception:
            # best-effort: инициализация уже состоялась, ошибки диагностики не критичны
            pass
    sys.stdout.write(jdumps(result))
    return 0

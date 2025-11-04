from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List
from typing import Tuple

# Ресурсы лежат под пакетом lg._skeletons/<preset>/lg-cfg/...
_SKELETONS_PKG = "lg._skeletons"


def list_presets() -> List[str]:
    """
    Перечислить доступные пресеты:
      • только директории внутри lg/_skeletons/
      • исключаем служебные ('.*', '_*', '__pycache__', '*.dist-info')
      • требуем наличие подкаталога 'lg-cfg'
    """
    try:
        base = resources.files(_SKELETONS_PKG)
    except Exception:
        return []
    out: List[str] = []
    for entry in base.iterdir():
        try:
            name = entry.name
            if not entry.is_dir():
                continue
            if name.startswith(".") or name.startswith("_") or name == "__pycache__" or name.endswith(".dist-info"):
                continue
            if not (entry / "lg-cfg").exists() or not (entry / "lg-cfg").is_dir():
                continue
            out.append(name)
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
        data = b""
        try:
            data = res.read_bytes()
        except Exception:
            # На некоторых платформах read_bytes может отсутствовать — fallback через open()
            with res.open("rb") as f:
                data = f.read()
        out.append((rel, data))
    out.sort(key=lambda t: t[0])
    return out


def init_cfg(
    *,
    repo_root: Path,
    preset: str = "basic",
    force: bool = False,
) -> Dict:
    """
    Разворачивает пресет в <repo_root>/lg-cfg/.
    Возвращает JSON-совместимый словарь с полями: ok, created, conflicts, preset.
    """
    repo_root = repo_root.resolve()
    target = (repo_root / "lg-cfg").resolve()

    # Составим план копирования
    created: List[str] = []
    conflicts: List[str] = []
    plan: List[Tuple[str, bytes]] = []

    # Собираем исходные файлы пресета
    try:
        src_entries = _collect_skeleton_entries(preset)
    except Exception as e:
        return {"ok": False, "error": str(e), "preset": preset}

    for rel, data in src_entries:
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
            "conflicts": sorted(conflicts),
            "message": "Use --force to overwrite existing files.",
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
    )
    sys.stdout.write(jdumps(result))
    return 0

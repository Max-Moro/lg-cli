from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict, List

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


@dataclass
class _CopyPlan:
    src: Path
    dst: Path


def _iter_skeleton_files(preset: str) -> List[Path]:
    """
    Возвращает список всех файлов в пресете (как временные файлы на FS через as_file()).
    Структура пресета: <preset>/lg-cfg/**/*
    """
    base = resources.files(_SKELETONS_PKG) / preset
    if not base.exists():
        raise RuntimeError(f"Preset not found: {preset}")
    out: List[Path] = []
    # Делаем проход только по файлам
    for p in (base / "lg-cfg").rglob("*"):
        try:
            if p.is_file():
                # as_file извлекает ресурс на FS, если он в zip/whl
                out.append(Path(resources.as_file(p).__enter__()))
        except Exception:
            continue
    out.sort()
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
    plan: List[_CopyPlan] = []

    # Собираем исходные файлы пресета
    try:
        src_files = _iter_skeleton_files(preset)
    except Exception as e:
        return {"ok": False, "error": str(e), "preset": preset}

    for src in src_files:
        # Относительный путь от корня lg-cfg/ в пресете
        # Находим «lg-cfg» в пути и берём хвост
        parts = src.as_posix().split("/")
        try:
            idx = parts.index("lg-cfg")
        except ValueError:
            # неожиданно — пропустим
            continue
        rel = "/".join(parts[idx + 1 :])
        if not _want_file(rel, include_examples=include_examples, include_models=include_models):
            skipped.append(rel)
            continue
        dst = target / rel
        if dst.exists() and not force:
            conflicts.append(rel)
            continue
        plan.append(_CopyPlan(src=src, dst=dst))

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
        for p in plan:
            rel = p.dst.resolve().relative_to(target).as_posix()
            if p.dst.exists():
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

    # Выполняем копирование
    for p in plan:
        p.dst.parent.mkdir(parents=True, exist_ok=True)
        # Копируем как текст/бинарь — shutil.copyfile корректен для любых ресурсов
        shutil.copyfile(p.src, p.dst)
        rel = p.dst.resolve().relative_to(target).as_posix()
        created.append(rel)

    return {
        "ok": True,
        "preset": preset,
        "target": str(target),
        "created": sorted(created),
        "skipped": sorted(skipped),
        "conflicts": sorted(conflicts) if force else [],
    }

from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import List, Optional, Dict

from .cache import Cache
from ..adapters import get_adapter_for_path
from ..config import DEFAULT_CONFIG_DIR
from ..config.model import Config
from ..filters.engine import FilterEngine
from ..lang import get_language_for_file
from ..utils import iter_files, read_file_text, build_pathspec


# --------------------------- Data model --------------------------- #
@dataclass
class FileEntry:
    fp: Path
    rel_path: str
    adapter: object
    text: str


@dataclass
class Group:
    lang: str
    entries: List[FileEntry]
    mixed: bool


@dataclass
class Plan:
    md_only: bool
    use_fence: bool
    groups: List[Group]


# --------------------------- Collection --------------------------- #
def _collect_changed_files(root: Path) -> set[str]:
    import subprocess
    def _git(args: list[str]) -> list[str]:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True, encoding="utf-8", errors="ignore"
        ).splitlines()
    files: set[str] = set()
    files.update(_git(["diff", "--name-only"]))
    files.update(_git(["diff", "--name-only", "--cached"]))
    files.update(_git(["ls-files", "--others", "--exclude-standard"]))
    return {Path(p).as_posix() for p in files if p}


def collect_entries(*, root: Path, cfg: Config, mode: str = "all") -> List[FileEntry]:
    """
    Единое место обхода ФС + фильтров + .gitignore + эвристик адаптеров.
    Возвращает упорядоченный список FileEntry.
    """
    exts = {e.lower() for e in cfg.extensions}
    spec_git = build_pathspec(root)
    engine = FilterEngine(cfg.filters)
    changed = _collect_changed_files(root) if mode == "changes" else None

    tool_dir = Path(__file__).resolve().parent.parent  # .../lg/
    cfg_dir = (root / DEFAULT_CONFIG_DIR).resolve()

    # auto-skip self code unless явно разрешён фильтрами
    skip_self_code = True
    try:
        rel_tool = tool_dir.resolve().relative_to(root.resolve()).as_posix()
        if (
            engine.includes(f"{rel_tool}/cli.py")
            or engine.includes(f"{rel_tool}/__init__.py")
        ):
            skip_self_code = False
    except ValueError:
        pass

    def _pruner(rel_dir: str) -> bool:
        try:
            (root / rel_dir).resolve().relative_to(cfg_dir)
            return False
        except ValueError:
            pass
        return engine.may_descend(rel_dir)

    out: List[FileEntry] = []
    for fp in iter_files(root, exts, spec_git, dir_pruner=_pruner):
        if skip_self_code and (tool_dir in fp.resolve().parents):
            continue
        rel_posix = fp.relative_to(root).as_posix()
        if changed is not None and rel_posix not in changed:
            continue
        if not engine.includes(rel_posix):
            continue

        text = read_file_text(fp)
        adapter = get_adapter_for_path(fp)
        lang_cfg = getattr(cfg, adapter.name, None)

        # согласованная логика пропусков
        if adapter.name != "base":
            if adapter.should_skip(fp, text, lang_cfg):
                continue
        else:
            if cfg.skip_empty and not text.strip():
                continue

        out.append(FileEntry(fp=fp, rel_path=rel_posix, adapter=adapter, text=text))

    return out


# --------------------------- Planning --------------------------- #
def build_plan(entries: List[FileEntry], cfg: Config) -> Plan:
    """
    Строит план рендера/трансформации: md_only, use_fence, groups
    (группировка подряд по языку при включённом fence).
    """
    if not entries:
        return Plan(md_only=True, use_fence=False, groups=[])

    md_only = all(e.adapter.name == "markdown" for e in entries)
    use_fence = cfg.code_fence and not md_only
    langs = {get_language_for_file(e.fp) for e in entries}
    mixed = (not use_fence) and (len(langs) > 1)

    groups: List[Group] = []
    if use_fence:
        for lang, grp_iter in groupby(entries, key=lambda e: get_language_for_file(e.fp)):
            grp = list(grp_iter)
            groups.append(Group(lang=lang, entries=grp, mixed=False))
    else:
        # один «смешанный» блок
        # lang строкой тут не важен, но оставим пустую для консистентности
        groups.append(Group(lang="", entries=list(entries), mixed=mixed))

    return Plan(md_only=md_only, use_fence=use_fence, groups=groups)


# --------------------- Utility for stats --------------------- #
def collect_processed_blobs(
    *,
    root: Path,
    cfg: Config,
    mode: str = "all",
    cache: Optional[Cache] = None,
) -> List[tuple[str, int, str, Dict, str]]:
    """
    (rel_path, size_raw_bytes, processed_text) — тексты ПОСЛЕ адаптеров
    с корректным group_size/mixed согласно плану.
    """
    entries = collect_entries(root=root, cfg=cfg, mode=mode)
    if not entries:
        return []

    plan = build_plan(entries, cfg)
    cache = cache or Cache(root)
    result: List[tuple[str, int, str, Dict, str]] = []

    for group in plan.groups:
        group_size = len(group.entries)
        for e in group.entries:
            cfg_lang = getattr(cfg, e.adapter.name, None)

            # --- кэшируем post-adapter результат ---
            key_hash, key_path = cache.build_key(
                abs_path=e.fp,
                adapter_name=e.adapter.name,
                adapter_cfg=cfg_lang,
                group_size=group_size,
                mixed=group.mixed,
            )
            cached = cache.get_processed(key_hash, key_path)
            if cached and "processed_text" in cached:
                processed = cached["processed_text"]
                meta = cached.get("meta", {})
            else:
                processed, meta = e.adapter.process_ex(e.text, cfg_lang, group_size, group.mixed)
                # сохраняем meta вместе с текстом (на будущее — для breakdown)
                try:
                    cache.put_processed(key_hash, key_path, processed_text=processed)
                    # дополнительно дописываем meta (без падений при ошибках)
                    with key_path.open("r+", encoding="utf-8") as f:
                        import json
                        data = json.load(f)
                        data["meta"] = meta
                        f.seek(0); f.truncate(0); json.dump(data, f, ensure_ascii=False)
                except Exception:
                    pass

            processed = processed.rstrip("\n") + "\n"
            # также возвращаем сырой текст e.text (нужен для raw-токенов)
            result.append((e.rel_path, e.fp.stat().st_size, processed, meta, e.text))

    return result

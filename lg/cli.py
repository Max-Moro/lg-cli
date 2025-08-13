from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from importlib import metadata
from pathlib import Path

from .config import (
    load_config,
    list_sections,
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_FILE,
    DEFAULT_SECTION_NAME, Config,
)
from .context import generate_context
from .context import list_context_names, collect_sections_for_context
from .core.generator import generate_listing
from .stats import (
    collect_stats_and_print,
    collect_stats,
    collect_context_stats,
    context_stats_and_print,
)

PROTOCOL_VERSION = 1


def _ensure_utf8_stdout_stderr() -> None:
    """
    На Windows консоль часто в cp1251 → любые юникод-символы (✓, эм-деши, «рамки»)
    могут привести к UnicodeEncodeError при sys.stdout.write(...).
    Если пользователь НЕ задал PYTHONIOENCODING/PYTHONUTF8, мягко переключаем stdout/stderr на UTF-8.
    """
    if os.environ.get("PYTHONIOENCODING") or os.environ.get("PYTHONUTF8"):
        return
    for stream_name in ("stdout", "stderr"):
        s = getattr(sys, stream_name, None)
        try:
            # Python 3.7+: доступен reconfigure()
            if hasattr(s, "reconfigure"):
                s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Не критично: в худшем случае остаётся системная кодировка.
            pass


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="listing-generator",
        description="Generate source listings or context-prompts based on lg-cfg/",
    )
    p.add_argument(
        "-s", "--section",
        default=DEFAULT_SECTION_NAME,
        help=(
            f"Section name from {DEFAULT_CONFIG_DIR}/{DEFAULT_CONFIG_FILE} "
            f"(default: {DEFAULT_SECTION_NAME})"
        ),
    )
    p.add_argument(
        "--list-sections",
        action="store_true",
        help="List available sections in the config and exit",
    )
    p.add_argument(
        "--list-contexts",
        action="store_true",
        help="List available context templates (from lg-cfg/contexts/*.tpl.md) and exit",
    )
    p.add_argument(
        "--doctor",
        action="store_true",
        help="Run environment checks and print a diagnostic report",
    )
    p.add_argument(
        "--context",
        metavar="PATH",
        help=(
            "Generate a prompt from template lg-cfg/contexts/PATH.tpl.md. "
            "PATH may include sub-directories, use forward slashes."
        ),
    )
    p.add_argument(
        "--context-stats",
        metavar="PATH",
        help=(
            "Compute aggregated stats for a context template (sum over all used sections, with file dedup). "
            "PATH is template name relative to lg-cfg/contexts/ (without .tpl.md)."
        ),
    )
    p.add_argument(
        "--mode",
        choices=("all", "changes"),
        default="all",
        help="all = entire project; changes = only modified git files",
    )
    p.add_argument(
        "--list-included",
        action="store_true",
        help="If set, only print included paths (debug mode)",
    )
    p.add_argument(
        "-v", "--verbose",
        action="count", default=0,
        help="Increase log verbosity (repeatable)",
    )
    # ── Управление code fence: по умолчанию берём из конфига.
    #    Явно включить → --code-fence, явно выключить → --no-code-fence
    grp_cf = p.add_mutually_exclusive_group()
    grp_cf.add_argument(
        "--code-fence",
        dest="code_fence",
        action="store_const",
        const=True,
        default=None,
        help="Force wrapping each file into fenced markdown block (```lang).",
    )
    grp_cf.add_argument(
        "--no-code-fence",
        dest="code_fence",
        action="store_const",
        const=False,
        help="Disable fenced code blocks regardless of config.yaml.",
    )
    p.add_argument(
        "--max-heading-level",
        type=int,
        default=None,
        help="Max heading level for Markdown normalization (overrides config)",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print size/token analytics instead of plain paths (use with --list-included)",
    )
    p.add_argument(
        "--stats-mode",
        choices=("raw", "processed", "rendered"),
        default="processed",
        help="Which text to count tokens for: raw file, post-adapter, or fully rendered listing.",
    )
    p.add_argument(
        "--sort",
        choices=("path", "size", "share"),
        default="path",
        help="Sorting column for --stats (default: path)",
    )
    p.add_argument(
        "--model",
        default="o3",
        help="Target LLM context window for --stats (default: o3)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON output for list/sections/contexts/stats/doctor",
    )
    return p

def _load_all_configs(cfg_path: Path) -> dict[str, Config]:
    """
    Утилита для веток --context/--context-stats: единоразово читаем все секции.
    """
    sections = list_sections(cfg_path)
    return {sec: load_config(cfg_path, sec) for sec in sections}

def _print_simple_list(items: list[str], as_json: bool, key: str) -> None:
    """
    Унифицированный вывод однотипных списков (--list-sections, --list-contexts).
    """
    if as_json:
        print(json.dumps({key: items}, ensure_ascii=False))
    else:
        for it in items:
            print(it)

def _run_doctor(root: Path, cfg_path: Path, as_json: bool) -> None:
    checks = []
    def add(name: str, ok: bool, details: str = ""):
        checks.append({"name": name, "ok": bool(ok), "details": details})

    # version/protocol
    try:
        ver = metadata.version("listing-generator")
    except Exception:
        ver = "(unknown)"
    add("cli.version", True, ver)
    add("cli.protocol", True, str(PROTOCOL_VERSION))

    # config presence & schema/sections
    if cfg_path.is_file():
        add("config.exists", True, str(cfg_path))
        try:
            secs = list_sections(cfg_path)
            add("config.schema", True, f"ok; sections={len(secs)}")
        except Exception as e:
            add("config.schema", False, str(e))
    else:
        add("config.exists", False, f"not found: {cfg_path}")

    # contexts dir
    ctx_dir = root / DEFAULT_CONFIG_DIR / "contexts"
    if ctx_dir.is_dir():
        cnt = len(list(ctx_dir.rglob("*.tpl.md")))
        add("contexts.exists", True, f"{cnt} template(s)")
    else:
        add("contexts.exists", False, f"no dir: {ctx_dir}")

    # git presence (optional)
    add("git.available", shutil.which("git") is not None, shutil.which("git") or "")

    # tiktoken presence (optional, for stats)
    try:
        import tiktoken  # noqa: F401
        add("tiktoken.available", True)
    except Exception as e:
        add("tiktoken.available", False, str(e))

    report = {
        "protocol": PROTOCOL_VERSION,
        "version": ver,
        "root": str(root),
        "checks": checks,
    }
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Listing Generator v{ver} (protocol {PROTOCOL_VERSION})")
        for c in checks:
            mark = "✔" if c["ok"] else "✖"
            extra = f" — {c['details']}" if c.get("details") else ""
            print(f"{mark} {c['name']}{extra}")


def main() -> None:
    ns = _build_parser().parse_args()

    # 1. Определяем корень (cwd) и путь до конфига
    root = Path.cwd()
    cfg_path = root / DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILE
    cfg_exists = cfg_path.is_file()

    # 2. Базовая настройка логирования
    logging.basicConfig(
        level=logging.WARNING - 10 * (ns.verbose or 0),
        format="%(levelname).1s:%(name)s: %(message)s",
    )

    # 2.1 Доктор может работать даже без конфига
    if ns.doctor:
        _run_doctor(root, cfg_path, ns.json)
        return

    if not cfg_exists:
        print(f"Error: Config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(2)

    # 3. Режим шаблонов (рендер или агрегированные stats)
    if ns.context:
        # Загружаем все секции один раз
        try:
            configs: dict[str, Config] = _load_all_configs(cfg_path)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(2)

        # Генерируем контекст
        try:
            generate_context(
                context_name=ns.context,
                configs=configs,
                list_only=ns.list_included,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(5)
        return

    if ns.context_stats:
        # Поднимаем все секции один раз
        try:
            configs_all: dict[str, Config] = _load_all_configs(cfg_path)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(2)
        try:
            used = collect_sections_for_context(
                ns.context_stats, root=root, configs=configs_all
            )
            if ns.json:
                data = collect_context_stats(
                    root=root,
                    configs=configs_all,
                    context_sections=used,
                    model_name=ns.model,
                )
                print(json.dumps(data, ensure_ascii=False))
            else:
                context_stats_and_print(
                    root=root,
                    configs=configs_all,
                    context_sections=used,
                    model_name=ns.model,
                    sort_key=getattr(ns, "sort", "path"),
                )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(5)
        return

    # 4. Режим списка секций
    if ns.list_sections:
        try:
            secs = list_sections(cfg_path)
            _print_simple_list(secs, ns.json, "sections")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(4)
        return

    # 4.1. Режим списка контекстов
    if ns.list_contexts:
        try:
            ctxs = list_context_names(root)
            _print_simple_list(ctxs, ns.json, "contexts")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(4)
        return

    # 5. Обычный режим листинга / list-included / stats
    try:
        cfg = load_config(cfg_path, ns.section)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)

    # Применяем CLI-overrides
    # code_fence: переопределяем только если флаг явно задан
    if ns.code_fence is not None:
        cfg.code_fence = bool(ns.code_fence)
    # max_heading_level (только если явно задан)
    if ns.max_heading_level is not None:
        cfg.markdown.max_heading_level = ns.max_heading_level

    if ns.list_included and ns.stats:
        if ns.json:
            data = collect_stats(
                root=root,
                cfg=cfg,
                mode=ns.mode,
                model_name=ns.model,
                stats_mode=getattr(ns, "stats_mode", "processed")
            )
            print(json.dumps(data, ensure_ascii=False))
        else:
            collect_stats_and_print(
                root=root,
                cfg=cfg,
                mode=ns.mode,
                sort_key=ns.sort,
                model_name=ns.model,
                stats_mode=getattr(ns, "stats_mode", "processed"),
            )
    else:
        if ns.list_included and ns.json:
            # JSON для --list-included: пути + размеры (без токенов)
            collected = generate_listing(
                root=root, cfg=cfg, mode=ns.mode, list_only=True, _return_stats=True
            )
            out = [
                {"path": rel, "sizeBytes": size}
                for (_fp, rel, size) in collected
            ]
            print(json.dumps({"files": out}, ensure_ascii=False))
        else:
            generate_listing(
                root=root,
                cfg=cfg,
                mode=ns.mode,
                list_only=ns.list_included,
            )


if __name__ == "__main__":
    _ensure_utf8_stdout_stderr()
    main()

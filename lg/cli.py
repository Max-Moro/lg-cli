from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .diag import run_diag
from .engine import run_report, run_render
from .jsonic import dumps as jdumps
from .migrate.errors import MigrationFatalError
from .types import RunOptions
from .version import tool_version


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lg",
        description="Listing Generator (context-first pipeline)",
        add_help=True,
    )
    p.add_argument("-v", "--version", action="version", version=f"%(prog)s {tool_version()}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Общие аргументы для render/report
    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "target",
            help="ctx:<name> | sec:<name> | <name> (сначала ищется контекст, иначе секция)",
        )
        sp.add_argument(
            "--model",
            default="o3",
            help="базовая модель для статистики",
        )
        sp.add_argument(
            "--mode",
            action="append",
            metavar="MODESET:MODE",
            help="активный режим в формате 'modeset:mode' (можно указать несколько)",
        )
        sp.add_argument(
            "--tags",
            help="дополнительные теги через запятую (например: python,tests,minimal)",
        )
        sp.add_argument(
            "--task",
            metavar="TEXT|@FILE|-",
            help=(
                "текст текущей задачи: прямая строка, @file для чтения из файла, "
                "или - для чтения из stdin"
            ),
        )

    sp_report = sub.add_parser("report", help="JSON-отчёт: статистика")
    add_common(sp_report)

    sp_render = sub.add_parser("render", help="Только финальный текст (не JSON)")
    add_common(sp_render)

    sp_list = sub.add_parser("list", help="Списки сущностей (JSON)")
    sp_list.add_argument("what", choices=["contexts", "sections", "models", "mode-sets", "tag-sets"], help="что вывести")

    sp_diag = sub.add_parser("diag", help="Диагностика окружения и конфига (JSON) [--bundle] [--rebuild-cache]")
    sp_diag.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="очистить и заново инициализировать кэш (.lg-cache) перед диагностикой",
    )
    sp_diag.add_argument(
        "--bundle",
        action="store_true",
        help="собрать диагностический бандл (.zip) с diag.json, lg-cfg и git-метаданными",
    )

    # Регистрация внешних подкоманд (расширяемость без правок CLI)
    try:
        from .scaffold import add_cli as _add_scaffold_cli
        _add_scaffold_cli(sub)
    except Exception:
        # best-effort: отсутствие модуля не должно ломать базовый CLI
        pass

    return p


def _opts(ns: argparse.Namespace) -> RunOptions:
    # Парсим режимы и теги
    modes = _parse_modes(getattr(ns, "mode", None))
    extra_tags = _parse_tags(getattr(ns, "tags", None))
    
    # Парсим task
    task_text = _parse_task(getattr(ns, "task", None))
    
    return RunOptions(
        model=ns.model,
        modes=modes,
        extra_tags=extra_tags,
        task_text=task_text,
    )


def _parse_modes(modes: list[str] | None) -> Dict[str, str]:
    """Парсит список режимов в формате 'modeset:mode' в словарь."""
    result = {}
    if not modes:
        return result
    
    for mode_spec in modes:
        if ":" not in mode_spec:
            raise ValueError(f"Invalid mode format '{mode_spec}'. Expected 'modeset:mode'")
        modeset, mode = mode_spec.split(":", 1)
        result[modeset.strip()] = mode.strip()
    
    return result


def _parse_tags(tags_str: str | None) -> set[str]:
    """Парсит строку тегов в множество."""
    if not tags_str:
        return set()
    
    return {tag.strip() for tag in tags_str.split(",") if tag.strip()}


def _parse_task(task_arg: Optional[str]) -> Optional[str]:
    """
    Парсит аргумент --task.
    
    Поддерживает три формата:
    - Прямая строка: "текст задачи"
    - Из файла: @path/to/file.txt
    - Из stdin: -
    
    Args:
        task_arg: Значение аргумента --task или None
        
    Returns:
        Текст задачи или None
    """
    if not task_arg:
        return None
    
    # Чтение из stdin
    if task_arg == "-":
        import sys
        content = sys.stdin.read().strip()
        return content if content else None
    
    # Чтение из файла
    if task_arg.startswith("@"):
        file_path = Path(task_arg[1:])
        if not file_path.exists():
            raise ValueError(f"Task file not found: {file_path}")
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            return content if content else None
        except Exception as e:
            raise ValueError(f"Failed to read task file {file_path}: {e}")
    
    # Прямая строка
    content = task_arg.strip()
    return content if content else None


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)

    try:
        # Унифицированный хук для внешних подкоманд: subparser.set_defaults(func=...)
        if hasattr(ns, "func") and callable(getattr(ns, "func")):
            rc = ns.func(ns)
            return int(rc) if isinstance(rc, int) else 0

        if ns.cmd == "report":
            result = run_report(ns.target, _opts(ns))
            sys.stdout.write(jdumps(result.model_dump(mode="json")))
            return 0

        if ns.cmd == "render":
            doc_text = run_render(ns.target, _opts(ns))
            sys.stdout.write(doc_text)
            return 0

        if ns.cmd == "list":
            root = Path.cwd()
            data: Dict[str, Any]
            if ns.what == "contexts":
                from .template import list_contexts
                data = {"contexts": list_contexts(root)}
            elif ns.what == "sections":
                from .config import list_sections
                data = {"sections": list_sections(root)}
            elif ns.what == "models":
                from .stats import list_models
                data = {"models": list_models(root)}
            elif ns.what == "mode-sets":
                from .config.modes import list_mode_sets
                mode_sets_result = list_mode_sets(root)
                data = mode_sets_result.model_dump(by_alias=True)
            elif ns.what == "tag-sets":
                from .config.tags import list_tag_sets
                tag_sets_result = list_tag_sets(root)
                data = tag_sets_result.model_dump(by_alias=True)
            else:
                raise ValueError(f"Unknown list target: {ns.what}")
            sys.stdout.write(jdumps(data))
            return 0

        if ns.cmd == "diag":
            report = run_diag(rebuild_cache=bool(getattr(ns, "rebuild_cache", False)))
            # По флагу --bundle собираем zip; путь пишем в stderr, stdout остаётся JSON
            if bool(getattr(ns, "bundle", False)):
                try:
                    from .diag.diagnostics import build_diag_bundle
                    bundle_path = build_diag_bundle(report)
                    sys.stderr.write(f"Diagnostic bundle written to: {bundle_path}\n")
                except Exception as e:
                    sys.stderr.write(f"Failed to build diagnostic bundle: {e}\n")
            sys.stdout.write(jdumps(report.model_dump(mode="json")))
            return 0

    except MigrationFatalError as e:
        sys.stderr.write(str(e).rstrip() + "\n")
        return 2
    except ValueError as e:
        sys.stderr.write(str(e).rstrip() + "\n")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

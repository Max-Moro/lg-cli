from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from .config import list_sections
from .context import list_contexts
from .diagnostics import run_diag
from .engine import run_report, run_render
from .jsonic import dumps as jdumps
from .migrate.errors import MigrationFatalError
from .stats import list_models
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
            "--mode",
            choices=["all", "changes"],
            default="all",
            help="область рабочего дерева",
        )
        sp.add_argument(
            "--model",
            default="o3",
            help="базовая модель для статистики",
        )
        sp.add_argument(
            "--no-fence",
            action="store_true",
            help="override конфигурации: отключить code fence",
        )

    sp_report = sub.add_parser("report", help="JSON-отчёт: статистика")
    add_common(sp_report)

    sp_render = sub.add_parser("render", help="Только финальный текст (не JSON)")
    add_common(sp_render)

    sp_list = sub.add_parser("list", help="Списки сущностей (JSON)")
    sp_list.add_argument("what", choices=["contexts", "sections", "models"], help="что вывести")

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

    # --- init (scaffold) ---
    sp_init = sub.add_parser("init", help="Инициализировать стартовую конфигурацию lg-cfg/ из упакованных пресетов")
    sp_init.add_argument(
        "--preset",
        default="basic",
        help="имя пресета (см. --list-presets)",
    )
    sp_init.add_argument(
        "--force",
        action="store_true",
        help="перезаписывать существующие файлы",
    )
    sp_init.add_argument(
        "--no-examples",
        action="store_true",
        help="не копировать примеры *.tpl.md и *.ctx.md",
    )
    sp_init.add_argument(
        "--with-models",
        action="store_true",
        help="положить пример lg-cfg/models.yaml (по умолчанию не создаём)",
    )
    sp_init.add_argument(
        "--dry-run",
        action="store_true",
        help="показать план действий, ничего не изменяя на диске",
    )
    sp_init.add_argument(
        "--list-presets",
        action="store_true",
        help="перечислить доступные пресеты и выйти",
    )

    return p


def _opts(ns: argparse.Namespace) -> RunOptions:
    return RunOptions(
        mode=ns.mode,
        model=ns.model,
        code_fence=not bool(getattr(ns, "no_fence", False)),
    )


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)

    try:
        if ns.cmd == "init":
            from .scaffold import list_presets, init_cfg
            if bool(getattr(ns, "list_presets", False)):
                data = {"presets": list_presets()}
                sys.stdout.write(jdumps(data))
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
            sys.stdout.write(jdumps(result))
            return 0

        if ns.cmd == "report":
            result = run_report(ns.target, _opts(ns))
            sys.stdout.write(jdumps(result.model_dump(mode="json")))
            return 0

        if ns.cmd == "render":
            doc = run_render(ns.target, _opts(ns))
            sys.stdout.write(doc.text)
            return 0

        if ns.cmd == "list":
            root = Path.cwd()
            data: Dict[str, Any]
            if ns.what == "contexts":
                data = {"contexts": list_contexts(root)}
            elif ns.what == "sections":
                data = {"sections": list_sections(root)}
            else:  # ns.what == "models" (choices enforce this)
                data = {"models": list_models(root)}
            sys.stdout.write(jdumps(data))
            return 0

        if ns.cmd == "diag":
            report = run_diag(rebuild_cache=bool(getattr(ns, "rebuild_cache", False)))
            # По флагу --bundle собираем zip; путь пишем в stderr, stdout остаётся JSON
            if bool(getattr(ns, "bundle", False)):
                try:
                    from .diagnostics import build_diag_bundle
                    bundle_path = build_diag_bundle(report)
                    sys.stderr.write(f"Diagnostic bundle written to: {bundle_path}\n")
                except Exception as e:
                    sys.stderr.write(f"Failed to build diagnostic bundle: {e}\n")
            sys.stdout.write(jdumps(report.model_dump(mode="json")))
            return 0

    except MigrationFatalError as e:
        sys.stderr.write(str(e).rstrip() + "\n")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

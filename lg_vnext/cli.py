from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .types import RunOptions
from .engine import run_report, run_render
from .context.resolver import list_contexts
from .config.load import list_sections, load_config_v6
from .jsonic import dumps as jdumps


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lg",
        description="Listing Generator vNext (context-first pipeline)",
        add_help=True,
    )
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

    sp_report = sub.add_parser("report", help="JSON-отчёт: статистика + rendered_text")
    add_common(sp_report)

    sp_render = sub.add_parser("render", help="Только финальный текст (не JSON)")
    add_common(sp_render)

    sp_list = sub.add_parser("list", help="Списки сущностей (JSON)")
    sp_list.add_argument("what", choices=["contexts", "sections"], help="что вывести")

    sub.add_parser("diag", help="Диагностика окружения и конфига (JSON)")

    return p


def _opts(ns: argparse.Namespace) -> RunOptions:
    return RunOptions(
        mode=ns.mode,
        model=ns.model,
        code_fence=not bool(getattr(ns, "no_fence", False)),
    )


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)

    if ns.cmd == "report":
        # Всегда pydantic-модель с .model_dump_json()
        result = run_report(ns.target, _opts(ns))
        sys.stdout.write(result.model_dump_json(ensure_ascii=False))  # type: ignore[attr-defined]
        return 0

    if ns.cmd == "render":
        doc = run_render(ns.target, _opts(ns))
        # Единственное место, где заботимся о переводе строки
        text = doc.text
        if not text.endswith("\n"):
            text += "\n"
        sys.stdout.write(text)
        return 0

    if ns.cmd == "list":
        root = Path.cwd()
        if ns.what == "contexts":
            data = {"contexts": list_contexts(root)}
        else:
            data = {"sections": list_sections(root)}
        sys.stdout.write(jdumps(data))
        return 0

    if ns.cmd == "diag":
        root = Path.cwd()
        try:
            cfg = load_config_v6(root)
            payload = {
                "protocol": 1,
                "root": str(root),
                "config": {
                    "schema_version": cfg.schema_version,
                    "sections": sorted(cfg.sections.keys()),
                },
                "contexts": list_contexts(root),
            }
        except Exception as e:
            payload = {
                "protocol": 1,
                "root": str(root),
                "config_error": str(e),
                "contexts": list_contexts(root),
            }
        sys.stdout.write(jdumps(payload))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

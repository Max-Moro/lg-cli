from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .types import RunOptions
from .engine import run_report, run_render

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lg", description="Listing Generator vNext")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("target", help="ctx:<name> | sec:<name> | <name> (ищется как контекст, затем секция)")
        sp.add_argument("--mode", choices=["all", "changes"], default="all", help="workspace scope")
        sp.add_argument("--model", default="o3", help="primary model for stats")
        # ВАЖНО: --max-heading-level отсутствует; управляется конфигом адаптера Markdown
        sp.add_argument("--no-fence", action="store_true", help="override config: disable code fence")

    sp_report = sub.add_parser("report", help="JSON report (stats + rendered text)")
    add_common(sp_report)

    sp_render = sub.add_parser("render", help="Plain rendered text")
    add_common(sp_render)

    sp_list = sub.add_parser("list", help="List contexts or sections")
    sp_list.add_argument("what", choices=["contexts", "sections"])

    sp_diag = sub.add_parser("diag", help="Diagnostics")

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
        res = run_report(ns.target, _opts(ns))
        # Если это pydantic-модель – у неё есть model_dump_json; иначе попробуем json.dumps
        try:
            s = res.model_dump_json(ensure_ascii=False)  # type: ignore[attr-defined]
        except Exception:
            try:
                from dataclasses import asdict
                s = json.dumps(asdict(res), ensure_ascii=False)
            except Exception:
                s = json.dumps(res, default=lambda o: getattr(o, "__dict__", str(o)), ensure_ascii=False)
        sys.stdout.write(s + ("\n" if not s.endswith("\n") else ""))
        return 0

    if ns.cmd == "render":
        doc = run_render(ns.target, _opts(ns))
        sys.stdout.write(doc.text)
        if not doc.text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if ns.cmd == "list":
        # Заглушки: реализацию подтянем в PR-2/3 (ContextResolver + loader)
        if ns.what == "contexts":
            sys.stdout.write("(stub) no contexts found\n")
        else:
            sys.stdout.write("(stub) sections: all\n")
        return 0

    if ns.cmd == "diag":
        # Минимальная диагностика до появления Diagnostics/loader
        root = Path.cwd()
        sys.stdout.write(f"LG vNext (protocol 1)\nroot: {root}\n")
        return 0

    return 2

if __name__ == "__main__":
    raise SystemExit(main())

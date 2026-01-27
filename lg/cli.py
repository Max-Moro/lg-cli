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
        prog="listing-generator",
        description="Listing Generator (context-first pipeline)",
        add_help=True,
    )
    p.add_argument("-v", "--version", action="version", version=f"%(prog)s {tool_version()}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Common arguments for render/report commands
    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "target",
            help="ctx:<name> | sec:<name> | <name> (context is searched first, then section)",
        )
        # Tokenization parameters
        sp.add_argument(
            "--lib",
            required=True,
            choices=["tiktoken", "tokenizers", "sentencepiece"],
            help="tokenization library"
        )
        sp.add_argument(
            "--encoder",
            required=True,
            help="encoder/model name"
        )
        sp.add_argument(
            "--ctx-limit",
            type=int,
            required=True,
            help="context window size in tokens"
        )
        sp.add_argument(
            "--mode",
            action="append",
            metavar="MODESET:MODE",
            help="active mode in 'modeset:mode' format (can be specified multiple times)",
        )
        sp.add_argument(
            "--tags",
            help="additional tags comma-separated (e.g.: python,tests,minimal)",
        )
        sp.add_argument(
            "--task",
            metavar="TEXT|@FILE|-",
            help=(
                "current task text: direct string, @file to read from file, "
                "or - to read from stdin"
            ),
        )
        sp.add_argument(
            "--target-branch",
            metavar="BRANCH",
            help=(
                "target branch for comparison when using vcs_mode: 'branch-changes'"
            ),
        )
        sp.add_argument(
            "--provider",
            metavar="PROVIDER",
            help="AI provider ID for provider: conditions in templates",
        )

    sp_report = sub.add_parser("report", help="JSON report: statistics")
    add_common(sp_report)

    sp_render = sub.add_parser("render", help="Final text only (not JSON)")
    add_common(sp_render)

    sp_list = sub.add_parser("list", help="Entity lists (JSON)")
    sp_list.add_argument(
        "what",
        choices=[
            "contexts",
            "sections",
            "mode-sets",
            "tag-sets",
            "tokenizer-libs",
            "encoders"
        ],
        help="what to output"
    )
    sp_list.add_argument(
        "--lib",
        choices=["tiktoken", "tokenizers", "sentencepiece"],
        help="library for encoder list (required for what=encoders)"
    )
    sp_list.add_argument(
        "--context",
        metavar="CTX",
        help="context name (required for mode-sets and tag-sets)"
    )
    sp_list.add_argument(
        "--provider",
        metavar="PROVIDER",
        help="provider ID (required for mode-sets, optional for contexts)"
    )

    sp_diag = sub.add_parser("diag", help="Environment and config diagnostics (JSON) [--bundle] [--rebuild-cache]")
    sp_diag.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="clear and reinitialize cache (.lg-cache) before diagnostics",
    )
    sp_diag.add_argument(
        "--bundle",
        action="store_true",
        help="create diagnostic bundle (.zip) with diag.json, lg-cfg and git metadata",
    )

    # Register external subcommands (extensibility without CLI modifications)
    try:
        from .scaffold import add_cli as _add_scaffold_cli
        _add_scaffold_cli(sub)
    except Exception:
        # best-effort: missing module should not break basic CLI
        pass

    return p


def _opts(ns: argparse.Namespace) -> RunOptions:
    # Parse modes and tags
    modes = _parse_modes(getattr(ns, "mode", None))
    extra_tags = _parse_tags(getattr(ns, "tags", None))

    # Parse task
    task_text = _parse_task(getattr(ns, "task", None))

    # Parse target-branch
    target_branch = getattr(ns, "target_branch", None)

    # Parse provider
    provider = getattr(ns, "provider", None)

    return RunOptions(
        tokenizer_lib=ns.lib,
        encoder=ns.encoder,
        ctx_limit=ns.ctx_limit,
        modes=modes,
        extra_tags=extra_tags,
        task_text=task_text,
        target_branch=target_branch,
        provider=provider,
    )


def _parse_modes(modes: list[str] | None) -> Dict[str, str]:
    """Parse list of modes in 'modeset:mode' format into a dictionary."""
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
    """Parse tags string into a set."""
    if not tags_str:
        return set()

    return {tag.strip() for tag in tags_str.split(",") if tag.strip()}


def _parse_task(task_arg: Optional[str]) -> Optional[str]:
    """
    Parse --task argument.

    Supports three formats:
    - Direct string: "task text"
    - From file: @path/to/file.txt
    - From stdin: -

    Args:
        task_arg: Value of --task argument or None

    Returns:
        Task text or None
    """
    if not task_arg:
        return None

    # Read from stdin
    if task_arg == "-":
        import sys
        content = sys.stdin.read().strip()
        return content if content else None

    # Read from file
    if task_arg.startswith("@"):
        file_path = Path(task_arg[1:])
        if not file_path.exists():
            raise ValueError(f"Task file not found: {file_path}")
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            return content if content else None
        except Exception as e:
            raise ValueError(f"Failed to read task file {file_path}: {e}")

    # Direct string
    content = task_arg.strip()
    return content if content else None


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)

    try:
        # Unified hook for external subcommands: subparser.set_defaults(func=...)
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
                provider = getattr(ns, "provider", None)
                if provider:
                    from .adaptive.listing import list_contexts_for_provider
                    data = {"contexts": list_contexts_for_provider(root, provider)}
                else:
                    from .template import list_contexts
                    data = {"contexts": list_contexts(root)}
            elif ns.what == "sections":
                from .section import list_sections
                data = {"sections": list_sections(root)}
            elif ns.what == "tokenizer-libs":
                from .stats import list_tokenizer_libs
                data = {"tokenizer_libs": list_tokenizer_libs()}
            elif ns.what == "encoders":
                if not ns.lib:
                    sys.stderr.write("Error: --lib is required for 'encoders'\n")
                    return 2
                from .stats import list_encoders
                data = {"lib": ns.lib, "encoders": list_encoders(ns.lib, root)}
            elif ns.what == "mode-sets":
                if not ns.context:
                    sys.stderr.write("Error: --context is required for 'mode-sets'\n")
                    return 2
                if not ns.provider:
                    sys.stderr.write("Error: --provider is required for 'mode-sets'\n")
                    return 2
                from .adaptive.listing import list_mode_sets
                try:
                    mode_sets_result = list_mode_sets(root, context=ns.context, provider=ns.provider)
                    data = mode_sets_result.model_dump(by_alias=True)
                except Exception as e:
                    sys.stderr.write(f"Error: {e}\n")
                    return 2
            elif ns.what == "tag-sets":
                if not ns.context:
                    sys.stderr.write("Error: --context is required for 'tag-sets'\n")
                    return 2
                from .adaptive.listing import list_tag_sets
                try:
                    tag_sets_result = list_tag_sets(root, context=ns.context)
                    data = tag_sets_result.model_dump(by_alias=True)
                except Exception as e:
                    sys.stderr.write(f"Error: {e}\n")
                    return 2
            else:
                raise ValueError(f"Unknown list target: {ns.what}")
            sys.stdout.write(jdumps(data))
            return 0

        if ns.cmd == "diag":
            report = run_diag(rebuild_cache=bool(getattr(ns, "rebuild_cache", False)))
            # With --bundle flag, create zip; write path to stderr, keep stdout as JSON
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

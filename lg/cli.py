from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from lg.config import load_config, list_sections, DEFAULT_CFG_FILE, DEFAULT_SECTION_NAME
from lg.core.generator import generate_listing

_LOG = logging.getLogger("lg")

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="listing-generator",
        description="Generate plain-text listing of project sources."
    )
    p.add_argument(
        "-c", "--config", default=DEFAULT_CFG_FILE,
        help=f"Path to listing_config.json (default: {DEFAULT_CFG_FILE})"
    )
    p.add_argument(
        "-s", "--section", default=DEFAULT_SECTION_NAME,
        help=f"Name of the configuration section to use (default: {DEFAULT_SECTION_NAME})"
    )
    p.add_argument(
        "--list-sections",
        action="store_true",
        help="List available sections in the config and exit"
    )
    p.add_argument(
        "--mode", choices=("all", "changes"), default="all",
        help="all = entire project; changes = only modified git files"
    )
    p.add_argument(
        "--root", default=".",
        help="Project root (searched for .git by default)"
    )
    p.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase log verbosity."
    )
    p.add_argument(
        "--list-included", action="store_true",
        help="Print only relative paths that pass filters (debug aid)."
    )
    return p

def main() -> None:                       # entry-point from pyproject
    parser = _build_parser()
    ns = parser.parse_args()

    # Опция --list-sections
    root = Path(ns.root).resolve()
    cfg_path = root / ns.config
    if ns.list_sections:
        try:
            sections = list_sections(cfg_path)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        for name in sections:
            print(name)
        sys.exit(0)

    logging.basicConfig(
        level=logging.WARNING - 10 * ns.verbose,
        format="%(levelname).1s:%(name)s: %(message)s"
    )

    root = Path(ns.root).resolve()
    cfg_path = root / ns.config
    try:
        cfg = load_config(cfg_path, ns.section)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    generate_listing(
        root=root,
        cfg=cfg,
        mode=ns.mode,
        list_only=ns.list_included,
    )

if __name__ == "__main__":
    main()

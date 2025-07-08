from __future__ import annotations

import argparse
import logging
from pathlib import Path

from lg.core.generator import generate_listing
from lg.config import load_config, DEFAULT_CFG_FILE

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
    return p

def main() -> None:                       # entry-point from pyproject
    parser = _build_parser()
    ns = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING - 10 * ns.verbose,
        format="%(levelname).1s:%(name)s: %(message)s"
    )

    root = Path(ns.root).resolve()
    cfg_path = root / ns.config
    cfg = load_config(cfg_path)

    generate_listing(
        root=root,
        cfg=cfg,
        mode=ns.mode,
    )

if __name__ == "__main__":
    main()

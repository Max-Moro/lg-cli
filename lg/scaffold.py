from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List
from typing import Tuple

# Resources are located under the package lg._skeletons/<preset>/...
_SKELETONS_PKG = "lg._skeletons"


def list_presets() -> List[str]:
    """
    List available presets:
      • all directories inside lg/_skeletons/
      • exclude Python artifacts ('__pycache__', '*.dist-info')
    """
    try:
        base = resources.files(_SKELETONS_PKG)
    except Exception:
        return []
    out: List[str] = []
    for entry in base.iterdir():
        try:
            name = entry.name
            if not entry.is_dir():
                continue
            if name == "__pycache__" or name.endswith(".dist-info"):
                continue
            out.append(name)
        except Exception:
            continue
    out.sort()
    return out


def _iter_all_files(node):
    """Recursive traversal of Traversable resources (compatible with .whl/zip)."""
    for entry in node.iterdir():
        if entry.is_dir():
            yield from _iter_all_files(entry)
        elif entry.is_file():
            yield entry


def _collect_skeleton_entries(preset: str) -> List[Tuple[str, bytes]]:
    """
    Collects (rel, data) pairs for all files from the preset.
    Preset structure: <preset>/**/* (files stored directly without lg-cfg/ wrapper)
    """
    root = resources.files(_SKELETONS_PKG) / preset
    if not root.exists():
        raise RuntimeError(f"Preset not found: {preset}")
    out: List[Tuple[str, bytes]] = []
    for res in _iter_all_files(root):
        rel = res.relative_to(root).as_posix()
        data = b""
        try:
            data = res.read_bytes()
        except Exception:
            # On some platforms read_bytes may be unavailable — fallback via open()
            with res.open("rb") as f:
                data = f.read()
        out.append((rel, data))
    out.sort(key=lambda t: t[0])
    return out


def init_cfg(
    *,
    repo_root: Path,
    preset: str = "basic",
    force: bool = False,
) -> Dict:
    """
    Deploys a preset to <repo_root>/lg-cfg/.
    Returns a JSON-compatible dict with fields: ok, created, conflicts, preset.
    """
    repo_root = repo_root.resolve()
    target = (repo_root / "lg-cfg").resolve()

    # Make a copy plan
    created: List[str] = []
    conflicts: List[str] = []
    plan: List[Tuple[str, bytes]] = []

    # Gather source files from preset
    try:
        src_entries = _collect_skeleton_entries(preset)
    except Exception as e:
        return {"ok": False, "error": str(e), "preset": preset}

    for rel, data in src_entries:
        dst = target / rel
        if dst.exists() and not force:
            conflicts.append(rel)
            continue
        plan.append((rel, data))

    # If there are conflicts and not force — exit/report
    if conflicts and not force:
        return {
            "ok": False,
            "preset": preset,
            "created": [],
            "conflicts": sorted(conflicts),
            "message": "Use --force to overwrite existing files.",
        }

    # Perform write
    for rel, data in plan:
        dst = (target / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            f.write(data)
        created.append(rel)

    return {
        "ok": True,
        "preset": preset,
        "target": str(target),
        "created": sorted(created),
        "conflicts": sorted(conflicts) if force else [],
    }

# ---------------- CLI glue ---------------- #

def add_cli(subparsers) -> None:
    """
    Registers the 'init' subcommand and binds handler via set_defaults(func=...).
    This allows developing CLI without changes to lg/cli.py.
    """
    sp = subparsers.add_parser(
        "init",
        help="Initialize initial lg-cfg/ configuration from packed presets",
    )
    sp.add_argument("--preset", default="basic", help="preset name (see --list-presets)")
    sp.add_argument("--force", action="store_true", help="overwrite existing files")
    sp.add_argument("--list-presets", action="store_true", help="list available presets and exit")
    # Handler — receives argparse.Namespace here
    sp.set_defaults(func=_run_cli, cmd="init")


def _run_cli(ns) -> int:
    """Handler for `lg init` subcommand."""
    from .jsonic import dumps as jdumps
    if bool(getattr(ns, "list_presets", False)):
        print(jdumps({"presets": list_presets()}))
        return 0

    root = Path.cwd()
    result = init_cfg(
        repo_root=root,
        preset=str(ns.preset),
        force=bool(getattr(ns, "force", False)),
    )
    sys.stdout.write(jdumps(result))
    return 0

"""
Utilities for working with CLI in tests.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Default tokenization parameters for tests
DEFAULT_TOKENIZER_LIB = "tiktoken"
DEFAULT_ENCODER = "cl100k_base"
DEFAULT_CTX_LIMIT = 128000


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    """
    Runs lg.cli with specified arguments in the given directory.

    Automatically adds required tokenization parameters (--lib, --encoder, --ctx-limit)
    for report and render commands, if not explicitly specified.

    Args:
        root: Working directory for command execution
        *args: Command line arguments for lg.cli

    Returns:
        CompletedProcess with execution results
    """
    # Convert args to list for modification
    args_list = list(args)

    # Check if tokenization parameters need to be added
    if _needs_tokenizer_params(args_list):
        args_list = _inject_tokenizer_params(args_list)
    
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args_list],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )


def _needs_tokenizer_params(args: list[str]) -> bool:
    """
    Checks if the command requires tokenization parameters.

    Parameters are needed for report and render commands, if not already specified.
    """
    if not args:
        return False

    # Check if the first argument is a command that requires tokenization
    command = args[0]
    if command not in ("report", "render"):
        return False

    # Check if tokenization parameters are already specified
    has_lib = "--lib" in args
    has_encoder = "--encoder" in args
    has_ctx_limit = "--ctx-limit" in args

    # If all parameters are already present, nothing needs to be added
    if has_lib and has_encoder and has_ctx_limit:
        return False

    return True


def _inject_tokenizer_params(args: list[str]) -> list[str]:
    """
    Adds default tokenization parameters to the arguments list.

    Inserts parameters after command (report/render) and target, but before other options.
    """
    # Find insertion position (after command and target)
    # Format: command target [--options]
    insert_pos = 2  # After command and target

    # If args has less than 2 elements, something is wrong, return as is
    if len(args) < 2:
        return args

    result = args[:insert_pos]

    # Add tokenization parameters if they are not present
    if "--lib" not in args:
        result.extend(["--lib", DEFAULT_TOKENIZER_LIB])

    if "--encoder" not in args:
        result.extend(["--encoder", DEFAULT_ENCODER])

    if "--ctx-limit" not in args:
        result.extend(["--ctx-limit", str(DEFAULT_CTX_LIMIT)])

    # Add remaining arguments
    result.extend(args[insert_pos:])

    return result


def jload(s: str):
    """
    Parses a JSON string, automatically removing ANSI escape codes.

    Some IDEs (e.g., PyCharm) may add ANSI escape sequences
    to subprocess output for colored console highlighting. This function removes such
    sequences before parsing JSON.

    Args:
        s: JSON string (possibly with ANSI escape codes)

    Returns:
        Parsed object
    """
    import re
    # Remove all ANSI escape sequences of the form \x1b[<digits>m
    # Examples: \x1b[0m (reset), \x1b[32m (green), \x1b[1;31m (bold red)
    clean = re.sub(r'\x1b\[[0-9;]*m', '', s)
    return json.loads(clean)


__all__ = [
    "run_cli",
    "jload",
    "DEFAULT_TOKENIZER_LIB",
    "DEFAULT_ENCODER",
    "DEFAULT_CTX_LIMIT",
]
"""
TypeScript file heuristics for identifying barrel files.
Separated into a dedicated module to simplify the main adapter.
"""

from __future__ import annotations

from ..context import LightweightContext
from ..tree_sitter_support import TreeSitterDocument


def is_barrel_file(lightweight_ctx: LightweightContext, adapter, tokenizer) -> bool:
    """
    Determine if file is a barrel file (index.ts or contains only re-exports).
    Uses lazy initialization - first simple heuristics, then parsing if needed.

    Args:
        lightweight_ctx: Lightweight context with file information
        adapter: Adapter for creating document if needed
        tokenizer: Tokenizer for parsing

    Returns:
        True if file is a barrel file
    """
    # Quick check by filename
    if lightweight_ctx.filename in ("index.ts", "index.tsx"):
        return True

    # Analyze content textually - if most lines contain export ... from
    lines = lightweight_ctx.raw_text.split('\n')
    export_lines = 0
    non_empty_lines = 0

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
            non_empty_lines += 1
            if 'export' in stripped and 'from' in stripped:
                export_lines += 1

    # If no significant lines, not barrel file
    if non_empty_lines == 0:
        return False

    # Heuristic: if more than 70% of lines are re-exports, consider barrel file
    export_ratio = export_lines / non_empty_lines

    # If obviously barrel file (many re-exports), return True
    if export_ratio > 0.7:
        return True

    # If obviously NOT barrel file (few re-exports), return False
    if export_ratio < 0.3:
        return False

    # For intermediate cases (30-70%) use lazy Tree-sitter initialization
    # for more accurate analysis of file structure
    try:
        full_context = lightweight_ctx.get_full_context(adapter, tokenizer)
        return _deep_barrel_file_analysis(full_context.doc)
    except Exception:
        # If Tree-sitter parsing failed, rely on text heuristic
        return export_ratio > 0.5


def _deep_barrel_file_analysis(doc: TreeSitterDocument) -> bool:
    """
    Deep analysis of barrel file through Tree-sitter parsing.
    Called only in complex cases.

    Args:
        doc: Parsed Tree-sitter document

    Returns:
        True if document is a barrel file
    """
    try:
        # Find all export statements
        exports = doc.query("exports")
        export_count = len(exports)

        # Find re-export statements (export ... from ...)
        reexport_count = 0
        for node, capture_name in exports:
            node_text = doc.get_node_text(node)
            if ' from ' in node_text:
                reexport_count += 1

        # Also find regular declarations (functions, classes, interfaces)
        functions = doc.query("functions")
        classes = doc.query("classes")
        interfaces = doc.query("interfaces")

        declaration_count = len(functions) + len(classes) + len(interfaces)

        # Barrel file if:
        # 1. Many re-exports and few own declarations
        # 2. Or very high percentage of re-exports
        if export_count > 0:
            reexport_ratio = reexport_count / export_count
            return reexport_ratio > 0.6 and declaration_count < 3

        return False

    except Exception:
        # On parsing errors return False
        return False


def should_skip_typescript_file(lightweight_ctx: LightweightContext, skip_barrel_files: bool, adapter, tokenizer) -> bool:
    """
    Determine if TypeScript file should be skipped entirely.

    Args:
        lightweight_ctx: Lightweight context with file information
        skip_barrel_files: Flag for skipping barrel files
        adapter: Adapter for creating document if needed
        tokenizer: Tokenizer for parsing

    Returns:
        True if file should be skipped
    """
    # Skip barrel files if the option is enabled
    if skip_barrel_files:
        if is_barrel_file(lightweight_ctx, adapter, tokenizer):
            return True

    # Can add other skip heuristics for TypeScript
    return False
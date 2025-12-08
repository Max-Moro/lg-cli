"""
Rust language descriptor for literal optimization.

Defines patterns for Rust literals: strings, arrays, vec!, HashMap blocks, lazy_static!.

Rust-specific patterns:
- String literals: regular ("...") and raw strings (r#"..."#)
- Array expressions: [elem1, elem2, ...]
- vec! macro: vec![elem1, elem2, ...]
- HashMap initialization blocks (imperative)

Note: Rust has no string interpolation in regular strings.
Format strings (`"{}..."`) exist but can't be reliably detected without runtime context.
"""

from __future__ import annotations

import re

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_raw_string_opening(text: str) -> str:
    """Detect Rust raw string opening delimiter (r#", r##", etc.)."""
    stripped = text.strip()
    # Match r, r#, r##, etc.
    match = re.match(r'^(r#+)"', stripped)
    if match:
        return match.group(0)  # e.g., r#"
    return '"'


def _detect_raw_string_closing(text: str) -> str:
    """Detect Rust raw string closing delimiter ("#, "##, etc.)."""
    stripped = text.strip()
    # Count hashes in opening to determine closing
    match = re.match(r'^(r#+)"', stripped)
    if match:
        hash_count = len(match.group(1)) - 1  # subtract 'r'
        return '"' + '#' * hash_count  # e.g., "#
    return '"'


# ============= Rust literal patterns =============

# String literals (regular and raw)
RUST_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    query="""
    [
      (string_literal) @lit
      (raw_string_literal) @lit
    ]
    """,
    opening=_detect_raw_string_opening,
    closing=_detect_raw_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
)

# Array expressions: [elem1, elem2, ...]
RUST_ARRAY = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    query="(array_expression) @lit",
    opening="[",
    closing="]",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

# vec! macro: vec![elem1, elem2, ...]
# Note: For Rust macros, the ! is part of the wrapper, not the opening delimiter
# So we search for "![" as opening to extract "vec" as wrapper
RUST_VEC_MACRO = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    query="""
    (macro_invocation
      macro: (identifier) @macro_name
      (#eq? @macro_name "vec")
      (token_tree)) @lit
    """,
    wrapper_match=r"^vec$",
    opening="![",
    closing="]",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="vec",
    priority=10,
)

# HashMap initialization pattern: let mut m = HashMap::new(); m.insert(...); ...
# Each let declaration is processed independently
RUST_HASHMAP_INIT = LiteralPattern(
    category=LiteralCategory.BLOCK_INIT,
    query="""
    (let_declaration
      value: (call_expression
        function: (scoped_identifier
          name: (identifier) @method_name)
        (#eq? @method_name "new"))) @lit
    """,
    opening="",
    closing="",
    statement_pattern="*/call_expression",
    min_elements=1,
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    comment_name="hashmap init",
    priority=15,
)

def create_rust_descriptor() -> LanguageLiteralDescriptor:
    """Create Rust language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        patterns=[
            RUST_HASHMAP_INIT,   # Priority 15: HashMap initialization groups
            RUST_VEC_MACRO,      # Priority 10: vec! macro
            RUST_ARRAY,          # Regular arrays
            RUST_STRING,         # Strings (regular and raw)
        ]
    )

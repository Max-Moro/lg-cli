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

from ..optimizations.literals import *
from .literals_component import RustLetGroupProcessor


def _rust_raw_closing(text: str, opening: str) -> str:
    """
    Compute closing delimiter for Rust raw strings.

    Rust raw strings: r#"..."#, r##"..."##, etc.
    Closing mirrors the number of hashes in opening.

    Args:
        text: Full string text (unused, kept for signature consistency)
        opening: Matched opening delimiter (e.g., 'r#"', 'r##"')

    Returns:
        Closing delimiter (e.g., '"#', '"##')
    """
    # Count hashes in opening: r#" → 1 hash, r##" → 2 hashes
    hash_count = opening.count('#')
    return '"' + '#' * hash_count


RUST_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],
    triple_quote_styles=[],  # Rust has no triple quotes
    single_quote_styles=['"'],
    raw_string_patterns=[
        (r'^(r#+)"', _rust_raw_closing),  # r#"..."#, r##"..."##
    ],
    default_delimiter='"',
)

_rust_detector = DelimiterDetector(RUST_DELIMITER_CONFIG)


# Rust literal profiles

# String profile (regular and raw strings)
RUST_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (raw_string_literal) @lit
    ]
    """,
    opening=_rust_detector.detect_opening,
    closing=_rust_detector.detect_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
)

# Sequence profile for array expressions
RUST_ARRAY_PROFILE = SequenceProfile(
    query="(array_expression) @lit",
    opening="[",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

# Factory profile for vec! macro
# Note: For Rust macros, the ! is part of the wrapper
RUST_VEC_PROFILE = FactoryProfile(
    query="""
    (macro_invocation
      macro: (identifier) @macro_name
      (#eq? @macro_name "vec")
      (token_tree)) @lit
    """,
    wrapper_match=r"^vec$",
    opening="![",
    closing="]",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="vec",
)

# Block init profile for HashMap initialization: let mut m = HashMap::new(); m.insert(...); ...
# Each let declaration is processed independently
RUST_HASHMAP_INIT_PROFILE = BlockInitProfile(
    query="""
    (let_declaration
      value: (call_expression
        function: (scoped_identifier
          name: (identifier) @method_name)
        (#eq? @method_name "new"))) @lit
    """,
    block_selector=None,  # No block selector for let_declaration
    statement_pattern="*/call_expression",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    min_elements=1,
    comment_name="hashmap init",
)

def create_rust_descriptor() -> LanguageLiteralDescriptor:
    """Create Rust language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            RUST_STRING_PROFILE,
            RUST_ARRAY_PROFILE,
            RUST_VEC_PROFILE,
            RUST_HASHMAP_INIT_PROFILE,
        ],
        custom_processor=RustLetGroupProcessor,
    )

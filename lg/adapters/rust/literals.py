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
    StringProfile,
    SequenceProfile,
    FactoryProfile,
    LanguageSyntaxFlags,
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


# ============= Rust literal profiles (v2) =============

# String profile (regular and raw strings)
RUST_STRING_PROFILE = StringProfile(
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
    priority=10,
)

# ============= Legacy patterns (BLOCK_INIT - will migrate on stage 1.13) =============

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
        # Language syntax flags
        syntax=LanguageSyntaxFlags(
            single_line_comment="//",
            block_comment_open="/*",
            block_comment_close="*/",
            supports_raw_strings=True,           # Rust has raw strings r#"..."#
            supports_template_strings=False,     # Rust has no template strings
            supports_multiline_strings=True,     # Raw strings can be multiline
            factory_wrappers=["vec"],            # vec! macro
            supports_block_init=True,            # Rust has HashMap initialization blocks
            supports_ast_sequences=False,        # Rust has no concatenated strings
        ),

        # String profiles
        string_profiles=[RUST_STRING_PROFILE],

        # Sequence profiles
        sequence_profiles=[RUST_ARRAY_PROFILE],

        # Factory profiles
        factory_profiles=[RUST_VEC_PROFILE],

        # Legacy patterns (BLOCK_INIT - will migrate on stage 1.13)
        _patterns=[RUST_HASHMAP_INIT],
    )

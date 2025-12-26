"""
Centralized placeholder management system for language adapters.
Provides unified API and intelligent placeholder collapsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Tuple, Optional

from .comment_style import CommentStyle
from .range_edits import RangeEditor
from .tree_sitter_support import Node, TreeSitterDocument


class PlaceholderAction(Enum):
    """Action type for placeholder - determines text suffix."""
    OMIT = "omitted"       # Complete removal of element
    TRUNCATE = "truncated"  # Partial reduction/trimming


# Pluralization rules for element types
_PLURAL_FORMS: Dict[str, str] = {
    "class": "classes",
    "property": "properties",
    "body": "bodies",
}


def _pluralize(word: str, count: int) -> str:
    """Pluralize word based on count."""
    if count == 1:
        return word
    # Check special forms
    if word in _PLURAL_FORMS:
        return _PLURAL_FORMS[word]
    # Default: add 's'
    return word + "s"


@dataclass
class PlaceholderSpec:
    """
    Placeholder specification with metadata.
    Stores structured placeholder information without binding to a specific format.
    """
    # Position in file (required)
    start_char: int
    end_char: int

    # Element type: "function", "method", "import", "comment", "literal", etc.
    # For bodies use: "function_body", "method_body", "getter_body", etc.
    element_type: str

    # Action: OMIT (complete removal) or TRUNCATE (partial reduction)
    action: PlaceholderAction = PlaceholderAction.OMIT

    # Placeholder indentation prefix
    placeholder_prefix: str = ""

    # Number of elements (for imports, comments that can be merged)
    count: int = 1

    # Lines removed - only meaningful for body types, explicitly passed by optimizer
    lines_removed: int = 0

    # For TRUNCATE action — the shortened content
    replacement_text: Optional[str] = None

    # Flag to add suffix comment after element
    add_suffix_comment: bool = True

    # Tokens saved by this placeholder (for literal_* types, shown instead of lines)
    tokens_saved: Optional[int] = None

    # Flag to use composing_nested for replacement (for nested structures like literals)
    use_composing_nested: bool = False

    @property
    def width(self) -> int:
        """Width of placeholder in characters."""
        return self.end_char - self.start_char

    def overlaps(self, other: PlaceholderSpec) -> bool:
        """Check if this placeholder overlaps with another."""
        return not (self.end_char <= other.start_char or other.end_char <= self.start_char)

    def contains(self, other: PlaceholderSpec) -> bool:
        """Check if this placeholder completely contains another (nested)."""
        return self.start_char <= other.start_char and other.end_char <= self.end_char

    @property
    def position_key(self) -> Tuple[int, int]:
        """Key for sorting by position."""
        return self.start_char, self.end_char

    def can_merge_with(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Check if this placeholder can be merged with another.

        Merge conditions:
        - Same element type and action
        - Suitable types (not bodies)
        - No significant content between placeholders
        - TRUNCATE with replacement_text should not be collapsed (unique content)
        """
        if self.element_type != other.element_type:
            return False

        if self.action != other.action:
            return False

        # TRUNCATE with explicit replacement_text should not be collapsed
        if self.replacement_text is not None:
            return False

        # Cannot collapse body placeholders - they represent distinct function/method bodies
        if self.element_type.endswith("_body"):
            return False

        # Check content between placeholders
        return not self._has_significant_content_between(other, source_text)

    def _has_significant_content_between(self, other: PlaceholderSpec, source_text: str) -> bool:
        """
        Conservative check for significant content between placeholders.

        Uses strict approach: placeholders are merged only if there is truly no code between them -
        only empty lines, spaces and tabs. Also checks that placeholders have the same number
        of characters from the line start.

        Args:
            other: Another placeholder for comparison
            source_text: Source text of document

        Returns:
            True if there is any code between placeholders or different indentation, False if only whitespace and same indentation
        """

        # Determine range between placeholders
        if self.end_char <= other.start_char:
            # self goes before other
            start_char = self.end_char
            end_char = other.start_char
        elif other.end_char <= self.start_char:
            # other goes before self
            start_char = other.end_char
            end_char = self.start_char
        else:
            # Placeholders overlap - can merge
            return False

        # Get content between placeholders
        if start_char >= end_char:
            return False

        try:
            content_between = source_text[start_char:end_char]
        except (UnicodeDecodeError, IndexError):
            # On decoding errors, conservatively block merge
            return True

        # Conservative approach: any non-empty content blocks merge
        stripped = content_between.strip()
        if stripped:
            return True

        # Check number of characters from line start for each placeholder
        self_chars_from_line_start = self._count_chars_from_line_start(self.start_char, source_text)
        other_chars_from_line_start = self._count_chars_from_line_start(other.start_char, source_text)

        if self_chars_from_line_start != other_chars_from_line_start:
            return True

        return False

    def _count_chars_from_line_start(self, char_position: int, source_text: str) -> int:
        """
        Count number of characters from line start to given character position.

        Args:
            char_position: Character position in text
            source_text: Source text of document

        Returns:
            Number of characters from nearest '\n' on the left to position
        """
        # Go left from position and search for nearest '\n'
        for i in range(char_position - 1, -1, -1):
            if i < len(source_text) and source_text[i] == '\n':
                # Found '\n', count characters from it to position
                return char_position - i - 1

        # If '\n' not found, we're at the beginning of file
        return char_position
    
    def merge_with(self, other: PlaceholderSpec, source_text: str) -> PlaceholderSpec:
        """Create merged placeholder."""
        if not self.can_merge_with(other, source_text):
            raise ValueError("Cannot merge incompatible placeholders")

        # Merged boundaries
        start_char = min(self.start_char, other.start_char)
        end_char = max(self.end_char, other.end_char)

        return PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=self.element_type,
            action=self.action,
            placeholder_prefix=self.placeholder_prefix,
            count=self.count + other.count,
            lines_removed=self.lines_removed + other.lines_removed,
            use_composing_nested=True,  # Enable composition with nested placeholders
        )


class PlaceholderManager:
    """
    Central manager for placeholder management.
    Provides unified API and handles collapsing.
    """

    def __init__(self, doc: TreeSitterDocument, comment_style: CommentStyle, editor: Optional[RangeEditor] = None):
        self.doc = doc
        self.comment_style = comment_style
        self.editor = editor
        self.source_text = doc.text
        self.placeholders: List[PlaceholderSpec] = []

    # ============= Public API for adding placeholders =============

    def add_placeholder(
        self,
        element_type: str,
        start_char: int,
        end_char: int,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        placeholder_prefix: str = "",
        count: int = 1,
        replacement_text: Optional[str] = None,
        add_suffix_comment: bool = False,
        tokens_saved: Optional[int] = None,
        use_composing_nested: bool = False,
    ) -> None:
        """
        Add placeholder with explicit coordinates.

        Args:
            element_type: Type of element ("function_body", "literal_string", etc.)
            start_char: Start position in characters
            end_char: End position in characters
            action: OMIT for complete removal, TRUNCATE for partial reduction
            placeholder_prefix: Indentation prefix for placeholder text
            count: Number of elements (for merging similar placeholders)
            replacement_text: For TRUNCATE action — the shortened content
            add_suffix_comment: Flag to add suffix comment after element
            tokens_saved: Tokens saved (for literal_* types, shown instead of lines)
            use_composing_nested: Use composing_nested for nested structures (literals)
        """
        # Calculate lines_removed automatically
        lines_removed = self.doc.count_removed_lines(start_char, end_char)

        spec = PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=element_type,
            action=action,
            placeholder_prefix=placeholder_prefix,
            count=count,
            lines_removed=lines_removed,
            replacement_text=replacement_text,
            add_suffix_comment=add_suffix_comment,
            tokens_saved=tokens_saved,
            use_composing_nested=use_composing_nested,
        )
        self.placeholders.append(spec)

    def add_placeholder_for_node(
        self,
        element_type: str,
        node: Node,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        count: int = 1,
        replacement_text: Optional[str] = None,
        add_suffix_comment: bool = False,
        tokens_saved: Optional[int] = None,
        use_composing_nested: bool = False,
    ) -> None:
        """
        Add placeholder for Tree-sitter node.

        Args:
            element_type: Type of element
            node: Tree-sitter node to replace
            action: OMIT or TRUNCATE
            count: Number of elements
            replacement_text: For TRUNCATE action — the shortened content
            add_suffix_comment: Flag to add suffix comment after element
            tokens_saved: Tokens saved (for literal_* types)
            use_composing_nested: Use composing_nested for nested structures (literals)
        """
        start_char, end_char = self.doc.get_node_range(node)

        # Calculate lines_removed automatically
        lines_removed = self.doc.count_removed_lines(start_char, end_char)

        spec = PlaceholderSpec(
            start_char=start_char,
            end_char=end_char,
            element_type=element_type,
            action=action,
            count=count,
            lines_removed=lines_removed,
            replacement_text=replacement_text,
            add_suffix_comment=add_suffix_comment,
            tokens_saved=tokens_saved,
            use_composing_nested=use_composing_nested,
        )
        self.placeholders.append(spec)

    # ============= Internal methods =============

    def _get_placeholder_content(self, spec: PlaceholderSpec) -> str:
        """
        Generate placeholder content based on metrics.

        Universal rules (metrics-based, not type-based):
        - If tokens_saved > 0: "type (−X tokens)" (simplified format)
        - Otherwise standard format: "… N type(s) action (X lines)"
          - count > 1: add count, pluralize type
          - lines_removed > 1 and != count: add lines suffix
        """
        element_type = spec.element_type
        display_type = element_type.replace("_", " ")

        # Token-based metric: simplified format without ellipsis/action
        # Example: "literal string (−X tokens)"
        if spec.tokens_saved is not None and spec.tokens_saved > 0:
            return f"{display_type} (−{spec.tokens_saved} tokens)"

        # Standard format: "… N type(s) action (X lines)"
        parts = ["…"]

        # Count prefix for multiple elements
        # Skip count for comments/docstrings - consecutive comments form a semantic unit
        show_count = spec.count > 1 and element_type not in ("comment", "docstring")
        if show_count:
            parts.append(str(spec.count))
            display_type = _pluralize(display_type, spec.count)

        parts.append(display_type)
        parts.append(spec.action.value)

        # Lines suffix when lines > 1 and differs from count
        if spec.lines_removed > 1 and spec.lines_removed != spec.count:
            parts.append(f"({spec.lines_removed} lines)")

        return " ".join(parts)

    def _build_full_replacement(self, spec: PlaceholderSpec) -> Tuple[str, int]:
        """
        Build complete replacement text including suffix comment if needed.

        For suffix comments, extends the replacement range to include trailing
        punctuation (brackets, semicolons, commas) so the comment appears after them.

        Args:
            spec: Placeholder specification

        Returns:
            (full_replacement_text, extended_end_char)
        """
        # Optimizer provided replacement, PlaceholderManager does nothing
        # (used by literals with inline placeholders)
        if not spec.add_suffix_comment:
            # Optimizer must provide replacement_text
            if spec.replacement_text is None:
                raise ValueError(f"replacement_text required when add_suffix_comment=False")
            return spec.replacement_text, spec.end_char

        # PlaceholderManager must generate placeholder content
        content = self._get_placeholder_content(spec)

        # Docstrings always use native language wrapping (same for OMIT and TRUNCATE)
        if spec.element_type == "docstring":
            doc_start, doc_end = self.comment_style.doc_markers
            if doc_end:
                replacement = f"{spec.placeholder_prefix}{doc_start} {content} {doc_end}"
            else:
                # Single-line docstring style (e.g., /// for Rust, // for Go)
                replacement = f"{spec.placeholder_prefix}{doc_start} {content}\n"
            return replacement, spec.end_char

        # For OMIT (no replacement_text): generate standalone placeholder
        if spec.replacement_text is None:
            replacement = f"{spec.placeholder_prefix}{self.comment_style.single_line} {content}"
            return replacement, spec.end_char

        # For TRUNCATE (with replacement_text): add suffix comment after content

        # Analyze context after element for suffix comment positioning
        text_after = self.source_text[spec.end_char:] if spec.end_char < len(self.source_text) else ""
        line_remainder = text_after.split('\n')[0]

        offset, needs_block = self._find_comment_insertion_point(line_remainder)

        # Build suffix comment
        if needs_block:
            block_start, block_end = self.comment_style.multi_line
            suffix = f" {block_start} {content} {block_end}"
        else:
            suffix = f" {self.comment_style.single_line} {content}"

        # Include trailing punctuation before comment
        trailing_punct = line_remainder[:offset]
        full_replacement = spec.replacement_text + trailing_punct + suffix
        extended_end = spec.end_char + offset

        return full_replacement, extended_end

    def _find_comment_insertion_point(self, line_remainder: str) -> Tuple[int, bool]:
        """
        Find insertion point for suffix comment.

        Returns:
            (offset_to_include, needs_block_comment)
            - offset_to_include: how many chars of punctuation to absorb
            - needs_block_comment: True if code follows on same line
        """
        if not line_remainder.strip():
            return 0, False

        offset = 0

        # Skip closing brackets
        while offset < len(line_remainder) and line_remainder[offset] in ')]}':
            offset += 1

        # Check semicolon
        if offset < len(line_remainder) and line_remainder[offset] == ';':
            offset += 1
            after_semi = line_remainder[offset:].strip()
            return offset, bool(after_semi)

        # Check comma
        if offset < len(line_remainder) and line_remainder[offset] == ',':
            offset += 1
            after_comma = line_remainder[offset:].strip()
            needs_block = bool(after_comma) and after_comma[0] not in ')]}'
            return offset, needs_block

        # Check for remaining code
        remaining = line_remainder[offset:].strip()
        return offset, bool(remaining)

    # ============= Collapsing and finalization =============

    def raw_edits(self) -> List[PlaceholderSpec]:
        """
        Return raw edits for evaluation in the budget system.
        """
        return self.placeholders

    def apply_to_editor(
        self,
        is_economical: Optional[Callable[[str, str], bool]] = None
    ) -> None:
        """
        Apply all placeholders to editor (side-effect only).

        Args:
            is_economical: Optional callback (original_text, replacement) -> bool.
                           Returns True if replacement should be applied.
                           If None, all replacements are applied.
        """
        # Collapse placeholders
        collapsed_specs = self._collapse_placeholders()

        # Sort by width (smaller first) for proper nesting support
        # This ensures nested literals are applied before their parents
        sorted_specs = sorted(collapsed_specs, key=lambda s: s.width)

        for spec in sorted_specs:
            # Build full replacement (including suffix comment with punctuation if needed)
            replacement, end_char = self._build_full_replacement(spec)

            # Get original text for economy check
            original = self.source_text[spec.start_char:end_char]

            # Check if replacement is economical
            if is_economical is not None and not is_economical(original, replacement):
                continue

            # Single editor call per placeholder
            if spec.use_composing_nested:
                self.editor.add_replacement_composing_nested(
                    spec.start_char, end_char, replacement,
                    edit_type=None
                )
            else:
                self.editor.add_replacement(
                    spec.start_char, end_char, replacement,
                    edit_type=None
                )

    def _collapse_placeholders(self) -> List[PlaceholderSpec]:
        """
        Collapse adjacent placeholders of the same type.
        Works at data level, without text parsing.
        """
        if not self.placeholders:
            return []

        # Sort by position for correct adjacency check
        sorted_placeholders = sorted(self.placeholders, key=lambda p: p.position_key)

        # Separate top-level and nested placeholders
        # Nested placeholders are those completely contained within others
        top_level = []
        nested = []

        for placeholder in sorted_placeholders:
            is_nested = False
            for other in sorted_placeholders:
                if other is placeholder:
                    continue
                if other.contains(placeholder):
                    is_nested = True
                    nested.append(placeholder)
                    break

            if not is_nested:
                top_level.append(placeholder)

        # Collapse only top-level placeholders
        collapsed = []
        if top_level:
            current_group = [top_level[0]]

            for placeholder in top_level[1:]:
                # Check if can merge with current group
                can_merge = current_group and current_group[-1].can_merge_with(placeholder, self.doc.text)

                if can_merge:
                    current_group.append(placeholder)
                else:
                    # Finalize current group
                    collapsed.append(self._merge_group(current_group))
                    current_group = [placeholder]

            # Don't forget last group
            if current_group:
                collapsed.append(self._merge_group(current_group))

        # Add nested placeholders back (they are not grouped)
        # They will be applied before their parents due to width-based sorting in apply_to_editor
        collapsed.extend(nested)

        return collapsed

    def _merge_group(self, group: List[PlaceholderSpec]) -> PlaceholderSpec:
        """Merge group of placeholders into one."""
        if len(group) == 1:
            return group[0]

        # Sequentially merge all placeholders in group
        result = group[0]
        for placeholder in group[1:]:
            result = result.merge_with(placeholder, self.doc.text)

        return result

"""
Context analyzer for headings to determine optimal parameters
for including Markdown documents in templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

from .nodes import MarkdownFileNode
from ..nodes import TemplateAST, TextNode
from ..types import ProcessingContext


@dataclass(frozen=True)
class HeadingContext:
    """
    Heading context for Markdown document placeholder.

    Contains information about surrounding headings and recommended
    parameters for document inclusion.
    """
    placeholders_continuous_chain: bool
    placeholder_inside_heading: bool
    heading_level: int
    strip_h1: bool


@dataclass(frozen=True)
class HeadingInfo:
    """Information about heading in template."""
    line_number: int
    level: int
    title: str
    heading_type: str  # 'atx', 'setext', 'placeholder'


@dataclass(frozen=True)
class PlaceholderInfo:
    """Information about placeholder in template."""
    node_index: int
    line_number: int
    inside_heading: bool
    is_markdown: bool
    is_glob: bool


@dataclass(frozen=True)
class TemplateStructure:
    """
    Complete parsed structure of template AST.

    Built once, reused for all analyses.
    """
    headings: List[HeadingInfo]
    horizontal_rules: List[int]  # line numbers
    placeholders: List[PlaceholderInfo]
    line_map: Dict[int, int]  # node_index -> line_number


class MarkdownPatterns:
    """Centralized regex patterns for Markdown parsing."""

    ATX_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
    ATX_HEADING_ONLY = re.compile(r'^(#{1,6})\s*$')
    SETEXT_H1 = re.compile(r'^=+\s*$')
    SETEXT_H2 = re.compile(r'^-+\s*$')
    FENCED_BLOCK = re.compile(r'^```|^~~~')
    HORIZONTAL_RULE = re.compile(r'^\s{0,3}[-*_]{3,}\s*$')
    HEADING_MARKERS_WITH_TEXT = re.compile(r'^#{1,6}\s+.*?$')
    HEADING_MARKERS_ONLY = re.compile(r'^#{1,6}\s*$')


class TemplateStructureParser:
    """
    Parses template AST into complete structure in single pass.

    Builds headings, horizontal rules, placeholders, and line map.
    """

    def __init__(self):
        self.patterns = MarkdownPatterns()

    def parse(self, ast: TemplateAST) -> TemplateStructure:
        """Parse complete template structure in single pass."""
        headings: List[HeadingInfo] = []
        horizontal_rules: List[int] = []
        placeholders: List[PlaceholderInfo] = []
        line_map: Dict[int, int] = {}

        current_line = 0

        for node_idx, node in enumerate(ast):
            line_map[node_idx] = current_line

            if isinstance(node, TextNode):
                # Parse both headings and HRs from text in one pass
                text_headings, text_hrs = self._parse_text_content(node.text, current_line)
                headings.extend(text_headings)
                horizontal_rules.extend(text_hrs)

                # Check for heading with placeholder pattern
                if node_idx + 1 < len(ast) and isinstance(ast[node_idx + 1], MarkdownFileNode):
                    placeholder_heading = self._check_placeholder_heading(node, current_line)
                    if placeholder_heading:
                        headings.append(placeholder_heading)

                current_line += len(node.text.split('\n'))

            elif isinstance(node, MarkdownFileNode):
                # Record placeholder info
                inside_heading = self._is_placeholder_inside_heading(ast, node_idx)
                placeholders.append(PlaceholderInfo(
                    node_index=node_idx,
                    line_number=current_line,
                    inside_heading=inside_heading,
                    is_markdown=True,
                    is_glob=node.is_glob
                ))
                current_line += 1

            else:
                # Other node types
                current_line += 1

        return TemplateStructure(
            headings=headings,
            horizontal_rules=horizontal_rules,
            placeholders=placeholders,
            line_map=line_map
        )

    def _parse_text_content(self, text: str, start_line: int) -> Tuple[List[HeadingInfo], List[int]]:
        """
        Parse text for both headings and horizontal rules in single pass.

        Returns:
            Tuple of (headings, horizontal_rule_lines)
        """
        headings: List[HeadingInfo] = []
        hrs: List[int] = []

        lines = text.split('\n')
        current_line = start_line
        in_fenced_block = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Track fenced blocks
            if self.patterns.FENCED_BLOCK.match(line_stripped):
                in_fenced_block = not in_fenced_block
                current_line += 1
                continue

            if in_fenced_block:
                current_line += 1
                continue

            # Check for ATX headings
            heading = self._parse_atx_heading(line_stripped, current_line)
            if heading:
                headings.append(heading)
                current_line += 1
                continue

            # Check for Setext headings
            if i + 1 < len(lines):
                heading = self._parse_setext_heading(line_stripped, lines[i + 1], current_line)
                if heading:
                    headings.append(heading)

            # Check for horizontal rules
            if self.patterns.HORIZONTAL_RULE.match(line):
                if not self._is_setext_underline(lines, i):
                    hrs.append(current_line)

            current_line += 1

        return headings, hrs

    def _parse_atx_heading(self, line: str, line_number: int) -> Optional[HeadingInfo]:
        """Parse ATX heading (# Heading)."""
        match = self.patterns.ATX_HEADING.match(line)
        if match:
            return HeadingInfo(
                line_number=line_number,
                level=len(match.group(1)),
                title=match.group(2).strip(),
                heading_type='atx'
            )
        return None

    def _parse_setext_heading(self, line: str, next_line: str, line_number: int) -> Optional[HeadingInfo]:
        """Parse Setext heading (underlined)."""
        if not line:
            return None

        next_stripped = next_line.strip()

        if self.patterns.SETEXT_H1.match(next_stripped):
            return HeadingInfo(line_number, 1, line, 'setext')
        elif self.patterns.SETEXT_H2.match(next_stripped):
            return HeadingInfo(line_number, 2, line, 'setext')

        return None

    def _is_setext_underline(self, lines: List[str], line_index: int) -> bool:
        """Check if line is a Setext heading underline."""
        if line_index == 0:
            return False

        prev_line = lines[line_index - 1].strip()

        if not prev_line:
            return False

        if (self.patterns.ATX_HEADING.match(prev_line) or
            self.patterns.FENCED_BLOCK.match(prev_line) or
            self.patterns.HORIZONTAL_RULE.match(prev_line)):
            return False

        return True

    def _check_placeholder_heading(self, text_node: TextNode, current_line: int) -> Optional[HeadingInfo]:
        """Check for heading with placeholder pattern: ### ${...}"""
        lines = text_node.text.split('\n')
        if not lines:
            return None

        last_line = lines[-1]
        match = self.patterns.ATX_HEADING_ONLY.match(last_line)
        if match:
            heading_line = current_line + len(lines) - 1
            return HeadingInfo(
                line_number=heading_line,
                level=len(match.group(1)),
                title="[placeholder]",
                heading_type='placeholder'
            )
        return None

    def _is_placeholder_inside_heading(self, ast: TemplateAST, node_index: int) -> bool:
        """Check if placeholder is inside a heading line."""
        # Check previous node
        if node_index > 0:
            prev_node = ast[node_index - 1]
            if isinstance(prev_node, TextNode):
                lines = prev_node.text.split('\n')
                if lines and not prev_node.text.endswith('\n'):
                    last_line = lines[-1]
                    if (self.patterns.HEADING_MARKERS_WITH_TEXT.match(last_line) or
                        self.patterns.HEADING_MARKERS_ONLY.match(last_line)):
                        return True

        # Check next node
        if node_index + 1 < len(ast):
            next_node = ast[node_index + 1]
            if isinstance(next_node, TextNode):
                if not next_node.text.startswith('\n'):
                    # Placeholder and text on same line - check prev node again
                    return self._is_placeholder_inside_heading(ast, node_index) if node_index > 0 else False

        return False


class ChainAnalyzer:
    """Analyzes whether placeholders form continuous chains."""

    def __init__(self, structure: TemplateStructure):
        self.structure = structure

    def is_continuous_chain(self, target_index: int) -> bool:
        """
        Determine if target placeholder is part of continuous chain.

        Logic:
        - Globs always form chains (multiple docs)
        - Placeholders inside headings don't participate
        - Split by horizontal rules into segments
        - Within segment, headings between placeholders break chain
        """
        target_placeholder = next(
            (p for p in self.structure.placeholders if p.node_index == target_index),
            None
        )

        if not target_placeholder:
            return False

        # Globs always form chains
        if target_placeholder.is_glob:
            return True

        # Get regular (not in heading) markdown placeholders
        regular_placeholders = [
            p for p in self.structure.placeholders
            if p.is_markdown and not p.inside_heading
        ]

        if len(regular_placeholders) <= 1:
            return self._analyze_single_placeholder(target_placeholder)

        # Split into segments by HRs
        segments = self._split_by_horizontal_rules(regular_placeholders)

        # Find target's segment
        target_segment = next(
            (seg for seg in segments if target_index in [p.node_index for p in seg]),
            None
        )

        if not target_segment:
            return self._analyze_single_placeholder(target_placeholder)

        # Single placeholder in segment = isolated
        if len(target_segment) <= 1:
            return False

        # Check for headings between placeholders in segment
        for i in range(len(target_segment) - 1):
            if self._has_headings_between(target_segment[i].line_number, target_segment[i + 1].line_number):
                return False

        return True

    def _split_by_horizontal_rules(self, placeholders: List[PlaceholderInfo]) -> List[List[PlaceholderInfo]]:
        """Split placeholders into segments by horizontal rules."""
        if not self.structure.horizontal_rules:
            return [placeholders]

        segments = []
        current_segment = []

        for placeholder in placeholders:
            if current_segment:
                prev_line = current_segment[-1].line_number
                curr_line = placeholder.line_number

                # Check for HR between
                has_hr_between = any(
                    prev_line < hr_line < curr_line
                    for hr_line in self.structure.horizontal_rules
                )

                if has_hr_between:
                    segments.append(current_segment)
                    current_segment = [placeholder]
                else:
                    current_segment.append(placeholder)
            else:
                current_segment.append(placeholder)

        if current_segment:
            segments.append(current_segment)

        return segments

    def _has_headings_between(self, start_line: int, end_line: int) -> bool:
        """Check if there are headings between two line numbers."""
        return any(
            start_line < h.line_number < end_line
            for h in self.structure.headings
        )

    def _analyze_single_placeholder(self, placeholder: PlaceholderInfo) -> bool:
        """Analyze single placeholder for chain-ness."""
        if placeholder.is_glob:
            return True

        line = placeholder.line_number

        # Check for HRs before and after
        hrs_before = [hr for hr in self.structure.horizontal_rules if hr < line]
        hrs_after = [hr for hr in self.structure.horizontal_rules if hr > line]

        # Isolated by HRs on both sides
        if hrs_before and hrs_after:
            return False

        # Check headings
        headings_before = [h for h in self.structure.headings if h.line_number < line]
        headings_after = [h for h in self.structure.headings if h.line_number > line]

        # Single placeholder under heading, none after
        if headings_before and not headings_after:
            return False

        # Check if separated by same-level headings
        if headings_before and headings_after:
            if headings_after[0].level <= headings_before[-1].level:
                return False

        return True


class HeadingContextDetector:
    """Main detector for heading context."""

    def __init__(self):
        self.parser = TemplateStructureParser()

    def detect_context(self, processing_context: ProcessingContext) -> HeadingContext:
        """
        Analyze placeholder context and determine optimal parameters.

        Single entry point that orchestrates all analysis.
        """
        # Parse structure once
        structure = self.parser.parse(processing_context.ast)

        # Get target placeholder info
        placeholder = next(
            (p for p in structure.placeholders if p.node_index == processing_context.node_index),
            None
        )

        if not placeholder:
            # Fallback for non-placeholder nodes
            return HeadingContext(
                placeholders_continuous_chain=False,
                placeholder_inside_heading=False,
                heading_level=1,
                strip_h1=False
            )

        # Analyze chain
        chain_analyzer = ChainAnalyzer(structure)
        is_chain = chain_analyzer.is_continuous_chain(processing_context.node_index)

        # Find parent heading (returns None for root-level)
        parent_level_raw = self._find_parent_heading(
            placeholder.line_number,
            structure.headings,
            structure.horizontal_rules
        )

        # Normalize: use 0 for root-level cases (no parent)
        parent_level = 0 if parent_level_raw is None else parent_level_raw

        # Calculate final parameters
        heading_level, strip_h1 = self._calculate_parameters(
            placeholder.inside_heading,
            parent_level,
            is_chain
        )

        return HeadingContext(
            placeholders_continuous_chain=is_chain,
            placeholder_inside_heading=placeholder.inside_heading,
            heading_level=heading_level,
            strip_h1=strip_h1
        )

    def _find_parent_heading(
        self,
        placeholder_line: int,
        headings: List[HeadingInfo],
        horizontal_rules: List[int]
    ) -> Optional[int]:
        """Find parent heading level, considering HR resets."""
        # Find closest HR before placeholder
        closest_hr = max(
            (hr for hr in horizontal_rules if hr < placeholder_line),
            default=None
        )

        start_line = closest_hr if closest_hr is not None else 0

        # Find last heading between start_line and placeholder
        parent_level = None
        for heading in headings:
            if start_line <= heading.line_number < placeholder_line:
                parent_level = heading.level
            elif heading.line_number >= placeholder_line:
                break

        return parent_level

    def _calculate_parameters(
        self,
        inside_heading: bool,
        parent_level: int,
        is_chain: bool
    ) -> Tuple[int, bool]:
        """
        Calculate final heading_level and strip_h1.

        Args:
            inside_heading: Placeholder is inside a heading line
            parent_level: Parent heading level (0 for root-level)
            is_chain: Placeholders form continuous chain

        Returns:
            Tuple of (heading_level, strip_h1)
        """
        if inside_heading:
            # H1 from file replaces the heading content at parent level
            return max(parent_level, 1), False

        # Nest one level deeper than parent (or level 1 if parent_level=0)
        heading_level = min(parent_level + 1, 6)

        # Determine strip_h1:
        # - Root level (parent_level=0) → preserve H1 (False)
        # - Under heading (parent_level>0) → chain preserves, isolated removes
        strip_h1 = (parent_level > 0) and not is_chain

        return heading_level, strip_h1


def detect_heading_context_for_node(processing_context: ProcessingContext) -> HeadingContext:
    """
    Convenient function for analyzing heading context for a single node.

    Args:
        processing_context: Context for processing AST node

    Returns:
        HeadingContext with recommendations
    """
    detector = HeadingContextDetector()
    return detector.detect_context(processing_context)
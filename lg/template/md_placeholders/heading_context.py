"""
Context analyzer for headings to determine optimal parameters
for including Markdown documents in templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

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
    # Context information
    placeholders_continuous_chain: bool      # Placeholders form continuous chain
    placeholder_inside_heading: bool         # Placeholder inside heading

    # Contextually determined parameters for MarkdownCfg
    heading_level: int    # Recommended max_heading_level
    strip_h1: bool        # Recommended strip_h1


@dataclass(frozen=True)
class HeadingInfo:
    """Information about heading in template."""
    line_number: int
    level: int
    title: str
    heading_type: str  # 'atx', 'setext', 'placeholder'


@dataclass(frozen=True)
class PlaceholderPosition:
    """Information about placeholder position in template."""
    line_number: int
    node_index: int
    inside_heading: bool


class MarkdownPatterns:
    """Centralized patterns for Markdown parsing."""

    # ATX headings: # Heading
    ATX_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')

    # ATX headings with symbols only (for placeholders): ###
    ATX_HEADING_ONLY = re.compile(r'^(#{1,6})\s*$')

    # Setext headings (underlines)
    SETEXT_H1 = re.compile(r'^=+\s*$')
    SETEXT_H2 = re.compile(r'^-+\s*$')

    # Fenced code blocks
    FENCED_BLOCK = re.compile(r'^```|^~~~')

    # Horizontal rules (context separators)
    HORIZONTAL_RULE = re.compile(r'^\s{0,3}[-*_]{3,}\s*$')

    # Heading markers in line (to determine inside_heading)
    HEADING_MARKERS_WITH_TEXT = re.compile(r'^#{1,6}\s+.*?$')
    HEADING_MARKERS_ONLY = re.compile(r'^#{1,6}\s*$')


class TextLineProcessor:
    """Processor for analyzing text lines in templates."""

    def __init__(self, patterns: MarkdownPatterns):
        self.patterns = patterns

    def parse_headings_from_text(self, text: str, start_line: int) -> List[HeadingInfo]:
        """
        Extracts headings from a text block.

        Args:
            text: Text to analyze
            start_line: Starting line number

        Returns:
            List of found headings
        """
        headings = []
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

            current_line += 1

        return headings
    
    def _parse_atx_heading(self, line: str, line_number: int) -> Optional[HeadingInfo]:
        """Parses an ATX heading (# Heading)."""
        match = self.patterns.ATX_HEADING.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            return HeadingInfo(line_number, level, title, 'atx')
        return None

    def _parse_setext_heading(self, line: str, next_line: str, line_number: int) -> Optional[HeadingInfo]:
        """Parses a Setext heading (underline)."""
        if not line:
            return None

        next_line_stripped = next_line.strip()

        if self.patterns.SETEXT_H1.match(next_line_stripped):
            return HeadingInfo(line_number, 1, line, 'setext')
        elif self.patterns.SETEXT_H2.match(next_line_stripped):
            return HeadingInfo(line_number, 2, line, 'setext')

        return None
    
    def parse_horizontal_rules_from_text(self, text: str, start_line: int) -> List[int]:
        """
        Extracts horizontal rule positions from a text block.

        Args:
            text: Text to analyze
            start_line: Starting line number

        Returns:
            List of line numbers with horizontal rules
        """
        horizontal_rules = []
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

            # Check for horizontal rules (only outside fenced blocks)
            if self.patterns.HORIZONTAL_RULE.match(line):
                # Check that this is NOT a Setext heading underline
                if not self._is_setext_underline(lines, i):
                    horizontal_rules.append(current_line)

            current_line += 1

        return horizontal_rules
    
    def _is_setext_underline(self, lines: List[str], line_index: int) -> bool:
        """
        Checks if a line is a Setext heading underline.

        Args:
            lines: List of all text lines
            line_index: Index of the line to check

        Returns:
            True if the line is a Setext heading underline
        """
        if line_index == 0:
            return False

        # Check the previous line
        prev_line = lines[line_index - 1].strip()

        # Previous line must contain text (not be empty)
        if not prev_line:
            return False

        # Previous line should not be an ATX heading or other markup
        if (self.patterns.ATX_HEADING.match(prev_line) or
            self.patterns.FENCED_BLOCK.match(prev_line) or
            self.patterns.HORIZONTAL_RULE.match(prev_line)):
            return False

        return True


class PlaceholderAnalyzer:
    """Analyzer for placeholder positions and context."""

    def __init__(self, patterns: MarkdownPatterns):
        self.patterns = patterns

    def find_placeholder_position(self, ast: TemplateAST, node_index: int) -> PlaceholderPosition:
        """
        Determines the exact position of a placeholder in the template.

        Args:
            ast: Template AST
            node_index: Index of the target node

        Returns:
            Information about placeholder position
        """
        line_number = self._calculate_line_number(ast, node_index)
        inside_heading = self._is_inside_heading(ast, node_index)
        
        return PlaceholderPosition(line_number, node_index, inside_heading)
    
    def _calculate_line_number(self, ast: TemplateAST, node_index: int) -> int:
        """Calculates the line number for a node."""
        line_number = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                line_number += len(node.text.split('\n'))
            else:
                line_number += 1
        return line_number

    def _is_inside_heading(self, ast: TemplateAST, node_index: int) -> bool:
        """
        Determines if a placeholder is inside a heading.

        Checks patterns like: "### ${md:docs/api}" or "## API: ${md:docs/api}"
        """
        return (self._check_heading_before(ast, node_index) or
                self._check_heading_continuation(ast, node_index))
    
    def _check_heading_before(self, ast: TemplateAST, node_index: int) -> bool:
        """Checks for heading markers in the previous node."""
        if node_index <= 0:
            return False

        prev_node = ast[node_index - 1]
        if not isinstance(prev_node, TextNode):
            return False

        # Check the last line of the previous node
        lines = prev_node.text.split('\n')
        if not lines:
            return False

        last_line = lines[-1]

        # Placeholder on the same line if previous node doesn't end with newline
        if not prev_node.text.endswith('\n'):
            return (bool(self.patterns.HEADING_MARKERS_WITH_TEXT.match(last_line)) or
                    bool(self.patterns.HEADING_MARKERS_ONLY.match(last_line)))

        return False

    def _check_heading_continuation(self, ast: TemplateAST, node_index: int) -> bool:
        """Checks for heading continuation in the next node."""
        if node_index + 1 >= len(ast):
            return False

        next_node = ast[node_index + 1]
        if not isinstance(next_node, TextNode):
            return False

        # If next node doesn't start with newline - placeholder and text on same line
        if not next_node.text.startswith('\n'):
            # Check if there are heading markers in the previous node
            return self._check_heading_before(ast, node_index)

        return False


class ChainAnalyzer:
    """Analyzer for placeholder chains."""

    def __init__(self, placeholder_analyzer: PlaceholderAnalyzer):
        """
        Initializes the chain analyzer.

        Args:
            placeholder_analyzer: Analyzer for placeholder positions
        """
        self.placeholder_analyzer = placeholder_analyzer
    
    def is_continuous_chain(self, ast: TemplateAST, target_index: int, headings: List[HeadingInfo], horizontal_rules: Optional[List[int]] = None) -> bool:
        """
        Determines if placeholders form a continuous chain.

        Logic:
        - Placeholders with globs are always considered a continuous chain (insert multiple documents)
        - If there are headings or horizontal rules between md-placeholders, they do NOT form a chain
        - If there's only text or other placeholders between them - it's a chain
        - Placeholders inside headings do NOT participate in chain analysis
        """
        if horizontal_rules is None:
            horizontal_rules = []

        # Special case: placeholders with globs always form a chain
        target_node = ast[target_index]
        if isinstance(target_node, MarkdownFileNode) and target_node.is_glob:
            return True

        # Find only "regular" placeholders (not inside headings)
        regular_md_indices = self._find_regular_markdown_placeholder_indices(ast)

        if len(regular_md_indices) <= 1:
            return self._analyze_single_placeholder(ast, target_index, headings, horizontal_rules)

        # Split placeholders into segments by horizontal rules
        segments = self._split_placeholders_by_horizontal_rules(ast, regular_md_indices, horizontal_rules)

        # Find the segment containing the target placeholder
        target_segment = None
        for segment in segments:
            if target_index in segment:
                target_segment = segment
                break

        if not target_segment:
            return self._analyze_single_placeholder(ast, target_index, headings, horizontal_rules)

        # If segment has only one placeholder - it's isolated
        if len(target_segment) <= 1:
            return False

        # Check for headings between placeholders within the segment
        for i in range(len(target_segment) - 1):
            has_headings = self._has_headings_between(ast, target_segment[i], target_segment[i + 1], headings)
            if has_headings:
                return False

        return True

    def _find_regular_markdown_placeholder_indices(self, ast: TemplateAST) -> List[int]:
        """
        Finds indices of only "regular" Markdown placeholders (not inside headings).

        Placeholders inside headings don't participate in chain analysis
        because they have different semantics - they replace heading text.
        """
        regular_indices = []
        for i, node in enumerate(ast):
            if isinstance(node, MarkdownFileNode):
                # Check if placeholder is inside a heading
                placeholder_pos = self.placeholder_analyzer.find_placeholder_position(ast, i)
                if not placeholder_pos.inside_heading:
                    regular_indices.append(i)

        return regular_indices
    
    def _has_headings_between(self, ast: TemplateAST, start_idx: int, end_idx: int, headings: List[HeadingInfo]) -> bool:
        """Checks for headings between two nodes."""
        start_line = self._calculate_node_line(ast, start_idx)
        end_line = self._calculate_node_line(ast, end_idx)

        return any(start_line < heading.line_number < end_line for heading in headings)

    def _calculate_node_line(self, ast: TemplateAST, node_index: int) -> int:
        """Calculates the line number for a node."""
        line = 0
        for i, node in enumerate(ast):
            if i == node_index:
                break
            if isinstance(node, TextNode):
                line += len(node.text.split('\n'))
            else:
                line += 1
        return line
    
    def _analyze_single_placeholder(self, ast: TemplateAST, node_index: int, headings: List[HeadingInfo], horizontal_rules: Optional[List[int]] = None) -> bool:
        """
        Analyzes a single placeholder for "chain-ness".

        Placeholders with globs are always considered a chain.
        If a placeholder is surrounded by same-level headings or horizontal rules - it's separated.
        """
        if horizontal_rules is None:
            horizontal_rules = []

        # Special case: placeholders with globs always form a chain
        target_node = ast[node_index]
        if isinstance(target_node, MarkdownFileNode) and target_node.is_glob:
            return True

        placeholder_line = self._calculate_node_line(ast, node_index)

        # Check for horizontal rules near the placeholder
        rules_before = [r for r in horizontal_rules if r < placeholder_line]
        rules_after = [r for r in horizontal_rules if r > placeholder_line]

        # If there are horizontal rules before and after - it's isolated
        if rules_before and rules_after:
            return False

        headings_before = [h for h in headings if h.line_number < placeholder_line]
        headings_after = [h for h in headings if h.line_number > placeholder_line]

        # If there are headings before but none after — this is a single placeholder
        # under a heading, NOT a chain (strip_h1=True should apply)
        if headings_before and not headings_after:
            return False

        if headings_before and headings_after:
            last_before = headings_before[-1]
            first_after = headings_after[0]

            # If headings are at the same level - placeholder is separated
            if first_after.level <= last_before.level:
                return False

        return True

    def _has_horizontal_rules_between(self, ast: TemplateAST, start_idx: int, end_idx: int, horizontal_rules: List[int]) -> bool:
        """Checks for horizontal rules between two nodes."""
        start_line = self._calculate_node_line(ast, start_idx)
        end_line = self._calculate_node_line(ast, end_idx)

        return any(start_line < rule_line < end_line for rule_line in horizontal_rules)
    
    def _split_placeholders_by_horizontal_rules(self, ast: TemplateAST, placeholder_indices: List[int], horizontal_rules: List[int]) -> List[List[int]]:
        """
        Splits placeholders into segments by horizontal rules.

        Args:
            ast: Template AST
            placeholder_indices: List of placeholder indices
            horizontal_rules: List of line numbers with horizontal rules

        Returns:
            List of segments, where each segment is a list of placeholder indices
        """
        if not horizontal_rules:
            return [placeholder_indices]

        segments = []
        current_segment = []

        for placeholder_idx in placeholder_indices:
            placeholder_node = ast[placeholder_idx]
            if not isinstance(placeholder_node, MarkdownFileNode):
                continue

            # Get line number for the placeholder
            placeholder_line = self._get_node_line_number(ast, placeholder_idx)

            # Check if there's a horizontal rule before this placeholder
            # (if current segment is not empty)
            if current_segment:
                prev_placeholder_idx = current_segment[-1]
                prev_placeholder_line = self._get_node_line_number(ast, prev_placeholder_idx)

                # Is there a horizontal rule between previous and current placeholder?
                has_rule_between = any(prev_placeholder_line < rule_line < placeholder_line
                                     for rule_line in horizontal_rules)

                if has_rule_between:
                    # Start a new segment
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = [placeholder_idx]
                else:
                    # Continue current segment
                    current_segment.append(placeholder_idx)
            else:
                # First placeholder - start a segment
                current_segment.append(placeholder_idx)

        # Add the last segment
        if current_segment:
            segments.append(current_segment)

        return segments

    def _get_node_line_number(self, ast: TemplateAST, node_index: int) -> int:
        """
        Gets the line number of a node in the AST.

        IMPORTANT: Must use the same line counting logic as _parse_all_headings()
        to avoid off-by-one errors when matching headings with placeholders.
        """
        line_number = 0
        for i in range(node_index):
            node = ast[i]
            if isinstance(node, TextNode):
                # Must match _parse_all_headings(): count lines, not newlines
                # For text "line1\nline2\nline3": split gives 3 lines, count gives 2 newlines
                line_number += len(node.text.split('\n'))
            else:
                line_number += 1
        return line_number


class HeadingContextDetector:
    """
    Detector for heading context.
    """

    def __init__(self):
        self.patterns = MarkdownPatterns()
        self.text_processor = TextLineProcessor(self.patterns)
        self.placeholder_analyzer = PlaceholderAnalyzer(self.patterns)
        self.chain_analyzer = ChainAnalyzer(self.placeholder_analyzer)

    def detect_context(self, processing_context: ProcessingContext) -> HeadingContext:
        """
        Analyzes placeholder context and determines optimal parameters.

        Args:
            processing_context: Context for processing AST node

        Returns:
            HeadingContext with parameter recommendations
        """
        # 1. Parse all headings in template
        template_headings = self._parse_all_headings(processing_context.ast)

        # 2. Parse all horizontal rules in template
        horizontal_rules = self._parse_all_horizontal_rules(processing_context.ast)

        # 3. Determine placeholder position
        placeholder_pos = self.placeholder_analyzer.find_placeholder_position(processing_context.ast, processing_context.node_index)

        # 4. Find parent heading level considering horizontal rules
        parent_level = self._find_parent_heading_level(placeholder_pos.line_number, template_headings, horizontal_rules)

        # 5. Analyze placeholder chains considering horizontal rules
        is_chain = self.chain_analyzer.is_continuous_chain(processing_context.ast, processing_context.node_index, template_headings, horizontal_rules)


        # 6. Check if placeholder is isolated by horizontal rule
        isolated_by_hr = self._is_placeholder_isolated_by_horizontal_rule(
            placeholder_pos.line_number, horizontal_rules, template_headings
        )

        # 7. Calculate final parameters
        heading_level, strip_h1 = self._calculate_parameters(
            placeholder_pos.inside_heading, parent_level, is_chain, isolated_by_hr
        )

        return HeadingContext(
            placeholders_continuous_chain=is_chain,
            placeholder_inside_heading=placeholder_pos.inside_heading,
            heading_level=heading_level,
            strip_h1=strip_h1
        )
    
    def _parse_all_headings(self, ast: TemplateAST) -> List[HeadingInfo]:
        """
        Parses all headings from the template AST.

        Includes regular headings and headings with placeholders.
        """
        headings = []
        current_line = 0

        for node_idx, node in enumerate(ast):
            if isinstance(node, TextNode):
                # Parse headings from text
                text_headings = self.text_processor.parse_headings_from_text(node.text, current_line)
                headings.extend(text_headings)

                # Check for headings with placeholders
                placeholder_heading = self._check_placeholder_heading(ast, node_idx, current_line)
                if placeholder_heading:
                    headings.append(placeholder_heading)

                current_line += len(node.text.split('\n'))
            else:
                current_line += 1

        return headings
    
    def _parse_all_horizontal_rules(self, ast: TemplateAST) -> List[int]:
        """
        Parses all horizontal rules from the template AST.

        Returns:
            List of line numbers with horizontal rules
        """
        horizontal_rules = []
        current_line = 0

        for node in ast:
            if isinstance(node, TextNode):
                # Parse horizontal rules from text
                rules = self.text_processor.parse_horizontal_rules_from_text(node.text, current_line)
                horizontal_rules.extend(rules)
                current_line += len(node.text.split('\n'))
            else:
                current_line += 1

        return horizontal_rules
    
    def _check_placeholder_heading(self, ast: TemplateAST, node_idx: int, current_line: int) -> Optional[HeadingInfo]:
        """
        Checks if current node is part of a heading with a placeholder.

        Looks for pattern: TextNode("### ") + MarkdownFileNode
        """
        if not isinstance(ast[node_idx], TextNode):
            return None

        # Check the next node
        if node_idx + 1 >= len(ast) or not isinstance(ast[node_idx + 1], MarkdownFileNode):
            return None

        text_node = ast[node_idx]
        if isinstance(text_node, TextNode):
            lines = text_node.text.split('\n')
        else:
            return None

        if not lines:
            return None

        last_line = lines[-1]

        # Check that last line contains only heading symbols
        match = self.patterns.ATX_HEADING_ONLY.match(last_line)
        if match:
            level = len(match.group(1))
            # Calculate line number for the heading
            heading_line = current_line + len(lines) - 1

            return HeadingInfo(
                line_number=heading_line,
                level=level,
                title="[placeholder]",
                heading_type='placeholder'
            )

        return None
    
    def _find_parent_heading_level(self, placeholder_line: int, headings: List[HeadingInfo], horizontal_rules: List[int]) -> Optional[int]:
        """
        Finds the level of the nearest parent heading considering horizontal rules.

        Horizontal rule resets heading context to level 1.

        Returns:
            Level of parent heading or None if no parent headings found
        """
        parent_level = None

        # Find nearest horizontal rule before placeholder
        closest_rule = None
        for rule_line in horizontal_rules:
            if rule_line < placeholder_line:
                closest_rule = rule_line
            else:
                break

        # If there's a horizontal rule, analyze only headings after it
        start_line = closest_rule if closest_rule is not None else 0

        for heading in headings:
            if start_line <= heading.line_number < placeholder_line:
                parent_level = heading.level
            elif heading.line_number >= placeholder_line:
                break

        return parent_level
    
    def _is_placeholder_isolated_by_horizontal_rule(self, placeholder_line: int, horizontal_rules: List[int], headings: List[HeadingInfo]) -> bool:
        """
        Checks if placeholder is isolated by horizontal rule.

        A placeholder is considered isolated by a horizontal rule if:
        1. There is a horizontal rule before it
        2. There are no headings between the horizontal rule and placeholder
        """
        if not horizontal_rules:
            return False

        # Find nearest horizontal rule before placeholder
        closest_rule = None
        for rule_line in horizontal_rules:
            if rule_line < placeholder_line:
                closest_rule = rule_line
            else:
                break

        if closest_rule is None:
            return False

        # Check if there are headings between the horizontal rule and placeholder
        for heading in headings:
            if closest_rule < heading.line_number < placeholder_line:
                # There's a heading between the rule and placeholder - not isolated by rule
                return False

        return True
    
    def _calculate_parameters(self, inside_heading: bool, parent_level: Optional[int], is_chain: bool, isolated_by_hr: bool = False) -> Tuple[int, bool]:
        """
        Calculates final parameters for heading_level and strip_h1.

        Args:
            inside_heading: Placeholder inside heading
            parent_level: Level of parent heading or None if no parent headings found
            is_chain: Placeholders form a chain
            isolated_by_hr: Placeholder isolated by horizontal rule

        Returns:
            Tuple (heading_level, strip_h1)
        """
        # Case 1: Placeholder inside heading
        # Example: ### ${md:docs/api}
        # H1 from file replaces the content of H3 heading
        if inside_heading:
            # parent_level cannot be None for inside_heading (heading level always exists)
            return parent_level if parent_level is not None else 1, False

        # Case 2: No parent headings
        # Example: ${md:README} (no headings at all)
        # Example: ${md:README}\n---\n# License (heading exists but after placeholder)
        # Document is inserted as root-level
        if parent_level is None:
            return 1, False

        # Case 3: Placeholder isolated by horizontal rule
        # Example: ## Section\n---\n${md:docs/api}
        # Horizontal rule resets context -> new root section
        if isolated_by_hr:
            return 1, False

        # Case 4: Regular placeholders under parent heading
        # Example: ## Section\n${md:docs/api}\n${md:docs/guide}
        # Nesting: parent_level + 1 (limited to H6)
        heading_level = min(parent_level + 1, 6)

        # strip_h1 depends on whether placeholders form a chain:
        # - Chain (no separating headings): strip_h1 = false (H1 is preserved)
        # - Separated by headings: strip_h1 = true (H1 is removed)
        strip_h1 = not is_chain

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
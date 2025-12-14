"""
String interpolation handler component.

Handles detection of interpolation markers, adjustment of truncation points
to respect interpolation boundaries, and identification of interpolation regions
in string content.

Supports various interpolation syntaxes:
- Bracketed: ${...}, #{...}, {...}
- Simple identifiers: $name, @name
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Callable

from ..patterns import StringProfile


class InterpolationHandler:
    """
    Handles string interpolation boundary detection and truncation adjustment.

    This component ensures that string truncation respects interpolation
    boundaries, preventing cuts in the middle of interpolators like ${...}
    or #{...}.

    Interpolation markers are defined as tuples of (prefix, opening, closing):
    - ("$", "{", "}"): Matches ${...}
    - ("#", "{", "}"): Matches #{...}
    - ("", "{", "}"): Matches {...}
    - ("$", "", ""): Matches $identifier

    The prefix is used to locate the start of an interpolator.
    The opening/closing delimiters define bracketed interpolators.
    If opening/closing are empty, it's a simple identifier interpolator.
    """

    def get_active_markers(
        self,
        profile: StringProfile,
        opening: str,
    ) -> List[Tuple[str, str, str]]:
        """
        Determine which interpolation markers are active for this string.

        Some markers only apply when the string has specific characteristics:
        - Python {}: only for f-strings (opening starts with f/F)
        - Rust {}: only for format strings (detected via profile)
        - JS ${}: for template strings (backticks)

        Markers with a prefix (like $) are self-verifying via the prefix.
        Markers without prefix use the profile's interpolation_active callback
        to determine applicability to this specific string.

        Args:
            profile: The StringProfile containing interpolation marker definitions
            opening: The string opening delimiter (e.g., "'", '"', f"', `...)

        Returns:
            List of active interpolation markers as (prefix, opening, closing) tuples

        Example:
            >>> handler = InterpolationHandler()
            >>> markers = handler.get_active_markers(profile, 'f"')
            >>> # Returns [("", "{", "}")] for f-string
        """
        # Get interpolation markers from profile
        markers = profile.interpolation_markers
        if not markers:
            return []

        activation_callback = profile.interpolation_active
        active_markers = []

        for marker in markers:
            prefix, opening_delim, closing_delim = marker

            # Markers with a prefix (like "$" in "${...}") are self-checking
            if prefix:
                active_markers.append(marker)
            else:
                # Empty prefix markers - use callback if available
                if activation_callback is not None:
                    if activation_callback(opening):
                        active_markers.append(marker)
                else:
                    # No callback - assume marker is always active
                    active_markers.append(marker)

        return active_markers

    def adjust_truncation(
        self,
        truncated: str,
        original: str,
        markers: List[Tuple[str, str, str]],
    ) -> str:
        """
        Adjust truncation point to respect string interpolation boundaries.

        If truncation lands inside an interpolator like ${...} or #{...},
        extend the truncation to include the complete interpolator to preserve
        valid syntax and AST structure.

        Args:
            truncated: The truncated string content
            original: The original full string content
            markers: List of (prefix, opening, closing) tuples defining active
                     interpolation markers

        Returns:
            Adjusted truncated string that respects interpolation boundaries

        Example:
            >>> handler = InterpolationHandler()
            >>> original = "Hello ${name} world"
            >>> truncated = "Hello $"  # Cut inside interpolator
            >>> adjusted = handler.adjust_truncation(truncated, original, markers)
            >>> # Returns "Hello ${name}" to complete the interpolator
        """
        cut_pos = len(truncated)

        # Find all interpolation regions in original
        interpolators = self.find_interpolation_regions(original, markers)

        for start, end in interpolators:
            # If cut position is inside this interpolator
            if start < cut_pos <= end:
                # Extend to include the full interpolator
                return original[:end]

        return truncated

    def find_interpolation_regions(
        self,
        content: str,
        markers: List[Tuple[str, str, str]],
    ) -> List[Tuple[int, int]]:
        """
        Find all string interpolation regions in content.

        Scans the content for all occurrences of interpolation markers
        and returns the start/end positions of each interpolation region.

        Handles:
        - Bracketed interpolation: ${...}, #{...}, {...}
        - Simple identifiers: $name, @name
        - Nested braces and string literals inside interpolators

        Args:
            content: String content to search for interpolation regions
            markers: List of (prefix, opening, closing) tuples defining
                     interpolation markers to search for

        Returns:
            List of (start, end) tuples indicating interpolation boundaries,
            where end is exclusive (points one past the last character)

        Example:
            >>> handler = InterpolationHandler()
            >>> content = "Hello ${name}, you are #{age}"
            >>> markers = [("$", "{", "}"), ("#", "{", "}")]
            >>> regions = handler.find_interpolation_regions(content, markers)
            >>> # Returns [(6, 13), (20, 27)]
        """
        regions = []
        i = 0

        while i < len(content):
            found = False

            for prefix, opening_delim, closing_delim in markers:
                full_opener = prefix + opening_delim

                # Case 1: Bracketed interpolation like ${...}, #{...}, {...}
                if opening_delim and closing_delim:
                    if content[i:].startswith(full_opener):
                        brace_pos = i + len(prefix)
                        end = self._find_matching_brace(content, brace_pos)
                        if end != -1:
                            regions.append((i, end + 1))
                            i = end + 1
                            found = True
                            break

                # Case 2: Simple identifier like $name (no braces)
                elif prefix and not opening_delim:
                    if content[i:].startswith(prefix):
                        # Find end of identifier
                        end = self._find_identifier_end(content, i + len(prefix))
                        if end > i + len(prefix):
                            regions.append((i, end))
                            i = end
                            found = True
                            break

            if not found:
                i += 1

        return regions

    def _find_identifier_end(self, content: str, start: int) -> int:
        """
        Find the end of an identifier starting at position.

        An identifier consists of:
        - First character: letter or underscore
        - Remaining characters: letters, digits, or underscores

        Args:
            content: String content to search
            start: Position where identifier starts

        Returns:
            Position after the last character of the identifier.
            Returns start if no valid identifier found.

        Example:
            >>> handler = InterpolationHandler()
            >>> end = handler._find_identifier_end("name_123xyz", 0)
            >>> # Returns 11 (position after "name_123xyz")
        """
        i = start
        if i >= len(content):
            return start

        # First char must be letter or underscore
        if not (content[i].isalpha() or content[i] == '_'):
            return start

        i += 1
        while i < len(content) and (content[i].isalnum() or content[i] == '_'):
            i += 1

        return i

    def _find_matching_brace(self, content: str, start: int) -> int:
        """
        Find the matching closing brace for an opening brace at start position.

        Handles:
        - Nested braces at different depths
        - String literals inside interpolators (prevents counting braces in strings)
        - Escape sequences in strings

        Args:
            content: String content to search
            start: Position of opening brace ('{')

        Returns:
            Position of matching closing brace, or -1 if not found

        Example:
            >>> handler = InterpolationHandler()
            >>> content = "{name: {first}}"
            >>> pos = handler._find_matching_brace(content, 0)
            >>> # Returns 14 (position of final '}')
        """
        if start >= len(content) or content[start] != '{':
            return -1

        depth = 1
        i = start + 1
        in_string = False
        string_char: Optional[str] = None

        while i < len(content) and depth > 0:
            char = content[i]

            # Handle string literals inside interpolator
            if not in_string and char in '"\'`':
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check for escape (simple check: count preceding backslashes)
                if i > 0 and content[i - 1] != '\\':
                    in_string = False
                    string_char = None
            elif not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1

            i += 1

        if depth == 0:
            return i - 1  # Position of closing brace

        return -1

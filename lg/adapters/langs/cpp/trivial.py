"""
C++ trivial file detection.

Detects trivial header files that contain only:
- Include guards (#ifndef, #define, #endif)
- Forward declarations (class Foo;, struct Bar;)
- Namespace declarations with only forward declarations
- Comments
"""

from __future__ import annotations

from ...optimizations.trivial_files import TrivialFileAnalyzer
from ...context import LightweightContext
from ...tree_sitter_support import TreeSitterDocument


class CppTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial C++ header files with only forward declarations."""

    HEADER_EXTENSIONS = ("hpp", "hh", "hxx", "h")

    ALLOWED_TYPES = {
        "preproc_ifdef",
        "preproc_ifndef",
        "preproc_def",
        "preproc_endif",
        "preproc_include",
        "#ifndef",
        "#define",
        "#endif",
        "#include",
        "identifier",
        "comment",
        "declaration",
        "type_definition",
        "class_specifier",
        "struct_specifier",
        "namespace_definition",
        "namespace",
        "namespace_identifier",
        "declaration_list",
        "class",
        "struct",
        "type_identifier",
        ";",
        "{",
        "}",
        "system_lib_string",
        "string_literal",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """Check if C++ header is trivial (forward declarations only)."""
        # Only analyze headers
        if ctx.ext not in self.HEADER_EXTENSIONS:
            return False

        # Quick check: empty file is trivial
        text = ctx.raw_text.strip()
        if not text:
            return True

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_header(doc)

    def _analyze_header(self, doc: TreeSitterDocument) -> bool:
        """Analyze header for triviality."""
        return self._check_nodes_trivial(doc.root_node, doc)

    def _check_nodes_trivial(self, node, doc: TreeSitterDocument) -> bool:
        """Recursively check if all nodes are trivial."""
        for child in node.children:
            node_type = child.type

            # Preprocessor blocks need recursive check
            if node_type in ("preproc_ifdef", "preproc_ifndef"):
                if not self._check_nodes_trivial(child, doc):
                    return False
                continue

            # Namespace needs recursive check
            if node_type == "namespace_definition":
                if not self._check_namespace_trivial(child, doc):
                    return False
                continue

            if node_type not in self.ALLOWED_TYPES:
                return False

            # class/struct specifier with body is non-trivial
            if node_type in ("class_specifier", "struct_specifier"):
                if self._has_body(child):
                    return False

        return True

    def _check_namespace_trivial(self, node, doc: TreeSitterDocument) -> bool:
        """Check if namespace contains only trivial declarations."""
        for child in node.children:
            if child.type == "declaration_list":
                return self._check_nodes_trivial(child, doc)
        return True

    def _has_body(self, node) -> bool:
        """Check if class/struct has body (field_declaration_list)."""
        for child in node.children:
            if child.type == "field_declaration_list":
                return True
        return False


__all__ = ["CppTrivialAnalyzer"]

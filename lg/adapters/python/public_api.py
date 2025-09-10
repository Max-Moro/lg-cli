"""
Python-specific public API optimization logic.
"""

from __future__ import annotations

from typing import List, Tuple

from ..context import ProcessingContext
from ..tree_sitter_support import Node


class PythonPublicApiCollector:
    """Python-specific logic for collecting private elements in public API mode."""
    
    def __init__(self, adapter):
        self.adapter = adapter
    
    def collect_private_elements(self, context: ProcessingContext) -> List[Tuple[Node, str]]:
        """Collect Python-specific private elements for removal."""
        private_elements = []
        
        # Python-specific elements
        self._collect_variable_assignments(context, private_elements)
        
        return private_elements
    
    def _collect_variable_assignments(self, context: ProcessingContext, private_elements: List[Tuple[Node, str]]):
        """Collect Python variable assignments that should be removed in public API mode."""
        assignments = context.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                # Get the assignment statement node
                assignment_def = node.parent
                if assignment_def:
                    # Check if variable is public using name-based rules
                    is_public = self.adapter.is_public_element(assignment_def, context.doc)
                    is_exported = self.adapter.is_exported_element(assignment_def, context.doc)
                    
                    # For top-level variables, check public/exported status
                    should_remove = not (is_public and is_exported)
                    
                    if should_remove:
                        private_elements.append((assignment_def, "variable"))

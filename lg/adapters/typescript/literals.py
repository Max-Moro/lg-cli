"""TypeScript-specific literal optimization."""

from ..javascript.literals import JSLiteralHandler


class TypeScriptLiteralHandler(JSLiteralHandler):
    """Handler for TypeScript template literals (reuses JavaScript logic)."""
    pass  # TypeScript uses same template literal logic as JavaScript

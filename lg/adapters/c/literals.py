"""C-specific literal optimization."""

from ..cpp.literals import CppLiteralHandler


class CLiteralHandler(CppLiteralHandler):
    """Handler for C struct arrays (reuses C++ logic)."""
    pass  # C uses same logic as C++ for struct arrays and nested initializers

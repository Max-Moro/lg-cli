"""Comprehensive sample for Budget System tests (Python).

Includes:
- Many external/local imports
- Large literals (strings, lists, dicts)
- Mixed comments and docstrings
- Public/private functions, classes, methods
- If __name__ == '__main__' guard
"""

# … 13 imports omitted (12 lines)


MODULE_DOC = """
This module demonstrates a variety of language features to exercise the
BudgetController escalation sequence. The text here is quite verbose and
contains enough co…""" # literal string (−41 tokens)

BIG_LIST = [f"item_{i:04d}" for i in range(200)]

BIG_DICT = {
    "users": [{"id": i, "name": f"User {i}", "active": i % 2 == 0} for i in range(50)],
    # … (1 more, −60 tokens)
}


def public_function(data: str) -> str:
    """Public API function.

    This docstring has multiple sentences. When budget is constrained, the
    controller may reduce documentation to the first sentence.
    """
    # … function body omitted (2 lines)


# … function omitted (6 lines)


class PublicClass:
    """Public class exposed to users.

    Contains both public and private members, plus lengthy docstrings.
    """

    def __init__(self, name: str):
        # … method body omitted (2 lines)

    def public_method(self, x: int, y: int) -> int:
        """Add two numbers and return the result."""
        return x + y

    # … method omitted (3 lines)

    @property
    def public_property(self) -> str:
        """Public property."""
        return self.name

    # … method omitted (4 lines)


# … class omitted (4 lines)


def huge_processing_pipeline(values: List[int]) -> Tuple[int, int, int]:
    """A long body that can be stripped when budgets are tight."""
    # … function body omitted (9 lines)


def another_long_function():
    """Another long function body to enable stripping heuristics."""
    # … function body omitted (4 lines)


if __name__ == "__main__":
    inst = PublicClass("demo")
    print(public_function("hello"))
    print(inst.public_method(2, 3))

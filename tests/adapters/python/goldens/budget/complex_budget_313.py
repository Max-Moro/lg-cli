"""Comprehensive sample for Budget System tests (Python).

Includes:
- Many external/local imports
- Large literals (strings, lists…"""





  
  


MODULE_DOC = """
This module demonstrates a variety of language features to exercise the
BudgetController escalation sequence. The text here is quite verbose and
contains enough co…"""

BIG_LIST = [f"item_{i:04d}" for i in range(200)]

BIG_DICT = {
    "…": "…",
}


def public_function(data: str) -> str:
    """Public API function.

    This docstring has multiple sentences. When budget is constrained, the
    controller may reduce documentation to the first sentence.
    """





class PublicClass:
    """Public class exposed to users.

    Contains both public and private members, plus lengthy docstrings.
    """

    def __init__(self, name: str):

    def public_method(self, x: int, y: int) -> int:
        """Add two numbers and return the result."""

    

    @property
    def public_property(self) -> str:
        """Public property."""

    





def huge_processing_pipeline(values: List[int]) -> Tuple[int, int, int]:
    """A long body that can be stripped when budgets are tight."""


def another_long_function():
    """Another long function body to enable stripping heuristics."""


if __name__ == "__main__":
    inst = PublicClass("demo")
    print(public_function("hello"))
    print(inst.public_method(2, 3))

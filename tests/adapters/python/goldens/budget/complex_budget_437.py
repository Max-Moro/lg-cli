"""Comprehensive sample for Budget System tests (Python).

Includes:
- Many external/local imports
- Large literals (strings, lists…""" # literal string (−30 tokens)





  
  


MODULE_DOC = """
This module demonstrates a variety of language features to exercise the
BudgetController escalation sequence. The text here is quite verbose and
contains enough co…""" # literal string (−41 tokens)

BIG_LIST = [f"item_{i:04d}" for i in range(200)]

BIG_DICT = {
    "…": "…",
} # literal object (−90 tokens)


def public_function(data: str) -> str:
    """Public API function.

    This docstring has multiple sentences. When budget is constrained, the
    controller may reduce documentation to the first sentence.
    """
    
    return data.upper()





class PublicClass:
    """Public class exposed to users.

    Contains both public and private members, plus lengthy docstrings.
    """

    def __init__(self, name: str):
        self.name = name
        self._cache: Dict[str, Any] = {}

    def public_method(self, x: int, y: int) -> int:
        """Add two numbers and return the result."""
        return x + y

    

    @property
    def public_property(self) -> str:
        """Public property."""
        return self.name

    





def huge_processing_pipeline(values: List[int]) -> Tuple[int, int, int]:
    """A long body that can be stripped when budgets are tight."""
    total = 0
    count = 0
    maximum = -10**9
    for v in values:
        count += 1
        total += v
        if v > maximum:
            maximum = v
    return total, count, maximum


def another_long_function():
    """Another long function body to enable stripping heuristics."""
    data = [i * i for i in range(500)]
    s = sum(data)
    m = max(data)
    return s, m


if __name__ == "__main__":
    inst = PublicClass("demo")
    print(public_function("hello"))
    print(inst.public_method(2, 3))

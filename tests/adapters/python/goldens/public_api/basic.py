"""Module for testing public API filtering."""

from typing import List
from functools import lru_cache

# Module-level public variable
PUBLIC_CONSTANT = "available_to_all"

# Module-level private variable
# … variable omitted

# Module-level private implementation detail
# … variable omitted

def public_function(data: str) -> str:
    """Public function available to all users.
    
    This function is part of the public API and should
    be preserved when filtering for public-only code.
    """
    processed = _private_helper(data)
    return processed.upper()

# … 2 functions omitted (11 lines)

class PublicClass:
    """Public class available to external users.
    
    This class provides the main API functionality
    and should be preserved in public API filtering.
    """
    
    def __init__(self, name: str):
        """Public constructor."""
        self.name = name
        self._private_data = []
        self.__very_private_data = {}
    
    def public_method(self) -> str:
        """Public method accessible to all users."""
        return f"Public: {self.name}"
    
    # … 2 methods omitted (10 lines)
    
    @property
    def public_property(self) -> str:
        """Public property accessor."""
        return self.name
    
    # … method omitted (4 lines)

    @staticmethod
    def public_static_method() -> str:
        """Public static method."""
        return "Static public"
    
    # … 2 methods omitted (9 lines)

    @classmethod
    def public_class_method(cls) -> 'PublicClass':
        """Public class method."""
        return cls("default")
    
    # … method omitted (4 lines)

# … 2 classes omitted (15 lines)

# Special methods (dunder methods) - should be considered public
class SpecialMethodsClass:
    """Class with special methods."""
    
    def __init__(self, value: int):
        self.value = value
    
    def __str__(self) -> str:
        """String representation - public special method."""
        return f"Value: {self.value}"
    
    def __repr__(self) -> str:
        """Object representation - public special method."""
        return f"SpecialMethodsClass({self.value})"
    
    def __len__(self) -> int:
        """Length implementation - public special method."""
        return abs(self.value)
    
    def __eq__(self, other) -> bool:
        """Equality comparison - public special method."""
        return isinstance(other, SpecialMethodsClass) and self.value == other.value
    
    # … method omitted (3 lines)

# … function omitted (3 lines)

# Module execution guard - should be preserved as it's a common pattern
if __name__ == "__main__":
    # This should be preserved as it's a standard Python pattern
    obj = PublicClass("test")
    print(obj.public_method())
    print(public_function("hello world"))

def add_repr(cls):
    cls.__repr__ = lambda self: f"<{cls.__name__} {self.__dict__}>"
    return cls

# … class omitted (5 lines)

"""Module for testing public API filtering."""

import logging
from typing import List, Optional

# Module-level public variable
PUBLIC_CONSTANT = "available_to_all"

# Module-level private variable
_PRIVATE_CONSTANT = "internal_use_only"

# Module-level private implementation detail
__INTERNAL_CONSTANT = "very_private"

def public_function(data: str) -> str:
    """Public function available to all users.
    
    This function is part of the public API and should
    be preserved when filtering for public-only code.
    """
    processed = _private_helper(data)
    return processed.upper()

def _private_function(data: str) -> str:
    """Private function for internal use.
    
    This function should be filtered out when
    public_api_only mode is enabled.
    """
    return data.lower()

def __very_private_function() -> None:
    """Very private implementation detail.
    
    Uses double underscore naming convention.
    """
    pass

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
    
    def _protected_method(self) -> str:
        """Protected method for subclasses.
        
        Should be filtered out in public API mode.
        """
        return f"Protected: {self.name}"
    
    def __private_method(self) -> str:
        """Private method for internal use.
        
        Should be filtered out in public API mode.
        """
        return f"Private: {self.name}"
    
    @property
    def public_property(self) -> str:
        """Public property accessor."""
        return self.name
    
    @property 
    def _private_property(self) -> List:
        """Private property accessor."""
        return self._private_data
    
    @staticmethod
    def public_static_method() -> str:
        """Public static method."""
        return "Static public"
    
    @staticmethod
    def _private_static_method() -> str:
        """Private static method."""
        return "Static private"
    
    @classmethod
    def public_class_method(cls) -> 'PublicClass':
        """Public class method."""
        return cls("default")
    
    @classmethod
    def _private_class_method(cls) -> 'PublicClass':
        """Private class method."""
        return cls("private_default")

class _PrivateClass:
    """Private class for internal implementation.
    
    This entire class should be filtered out
    when public_api_only mode is enabled.
    """
    
    def __init__(self):
        self.data = "private"
    
    def process(self) -> str:
        """Method of private class."""
        return self.data.upper()

class __VeryPrivateClass:
    """Very private class using double underscore.
    
    Should definitely be filtered out.
    """
    pass

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
    
    def _helper_for_special_methods(self) -> str:
        """Private helper for special methods."""
        return f"Helper: {self.value}"

def _private_helper(data: str) -> str:
    """Private module-level helper function."""
    return data.strip()

# Module execution guard - should be preserved as it's a common pattern
if __name__ == "__main__":
    # This should be preserved as it's a standard Python pattern
    obj = PublicClass("test")
    print(obj.public_method())
    print(public_function("hello world"))

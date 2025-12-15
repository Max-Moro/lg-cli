"""Module docstring with detailed description."""

import os
import sys  # … comment omitted
from typing import List, Optional  # … comment omitted


class CommentedClass:
    """Class with various comment types."""
    
    def __init__(self, name: str):
        """Initialize with name."""
        # … comment omitted
        self.name = name
        self.data = []  # … comment omitted
    
    def public_method(self) -> str:
        """Get the name value."""
        # … comment omitted
        return self.name
    
    def _private_method(self):
        """Private method with documentation."""
        # … comment omitted
        temp = self.name.upper()
        return temp  # … comment omitted
    
    # … comment omitted
    def method_with_lots_of_comments(self):
        # … comment omitted
        value = "test"
        
        # … comment omitted
        processed = value.strip()
        
        # … comment omitted
        if not processed:
            # … comment omitted
            return None
            
        # … comment omitted
        return processed.lower()

def standalone_function():
    """Function with minimal documentation."""
    # … comment omitted
    pass

# … comment omitted
def undocumented_function():
    # … comment omitted
    x = 1  # … comment omitted
    y = 2  # … comment omitted
    return x + y  # … comment omitted

# … comment omitted
def function_with_annotations():
    """Function with TODO and FIXME annotations."""
    # … comment omitted
    result = "placeholder"
    # … comment omitted
    return result

if __name__ == "__main__":
    # … comment omitted
    obj = CommentedClass("test")
    print(obj.public_method())

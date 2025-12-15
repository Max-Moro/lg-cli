"""Module docstring with detailed description.

This module demonstrates various comment styles and documentation
patterns for testing comment optimization policies.
"""

import os
import sys  # … comment omitted
from typing import List, Optional  # … comment omitted


class CommentedClass:
    """Class with various comment types."""
    
    def __init__(self, name: str):
        """Initialize with name.
        
        Args:
            name: The name to set
            
        Returns:
            None
        """
        # … comment omitted
        self.name = name
        self.data = []  # … comment omitted
    
    def public_method(self) -> str:
        """Get the name value.
        
        This method returns the current name. It's a simple getter
        that provides access to the internal name field. 
        Very straightforward implementation.
        """
        # … comment omitted
        return self.name
    
    def _private_method(self):
        """Private method with documentation.
        
        This is an internal utility method.
        Should not be used externally.
        """
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
    """Function with TODO and FIXME annotations.
    
    This function needs improvement.
    """
    # … comment omitted
    result = "placeholder"
    # … comment omitted
    return result

if __name__ == "__main__":
    # … comment omitted
    obj = CommentedClass("test")
    print(obj.public_method())

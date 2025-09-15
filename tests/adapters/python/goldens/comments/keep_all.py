"""Module docstring with detailed description.

This module demonstrates various comment styles and documentation
patterns for testing comment optimization policies.
"""

import os
import sys  # Standard library import
from typing import List, Optional  # TODO: Consider using generics


class CommentedClass:
    """Class with various comment types."""
    
    def __init__(self, name: str):
        """Initialize with name.
        
        Args:
            name: The name to set
            
        Returns:
            None
        """
        # This is a regular comment
        self.name = name
        self.data = []  # FIXME: Should use better data structure
    
    def public_method(self) -> str:
        """Get the name value.
        
        This method returns the current name. It's a simple getter
        that provides access to the internal name field. 
        Very straightforward implementation.
        """
        # Regular comment before return
        return self.name
    
    def _private_method(self):
        """Private method with documentation.
        
        This is an internal utility method.
        Should not be used externally.
        """
        # Implementation details
        # Multiple line comment
        # explaining the logic
        temp = self.name.upper()
        return temp  # Another trailing comment
    
    # Class-level comment
    def method_with_lots_of_comments(self):
        # Start of method
        value = "test"
        
        # First processing step
        # This handles the initial data
        processed = value.strip()
        
        # Second processing step - validation
        if not processed:
            # Handle empty case
            return None
            
        # Final step - return result
        # NOTE: Could be optimized
        return processed.lower()

def standalone_function():
    """Function with minimal documentation."""
    # Just a simple comment
    pass

# Module-level comment
def undocumented_function():
    # No docstring, just comments
    # This function doesn't have proper documentation
    x = 1  # Simple assignment
    y = 2  # Another assignment  
    return x + y  # Return sum

# TODO: Implement better error handling
def function_with_annotations():
    """Function with TODO and FIXME annotations.
    
    This function needs improvement.
    """
    # FIXME: This logic is flawed
    result = "placeholder"
    # WARNING: Not implemented properly
    return result

if __name__ == "__main__":
    # Main execution comment
    obj = CommentedClass("test")
    print(obj.public_method())

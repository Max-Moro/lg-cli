# … docstring omitted

import os
import sys  # … comment omitted
from typing import List, Optional  # … comment omitted


class CommentedClass:
    # … docstring omitted
    
    def __init__(self, name: str):
        # … docstring omitted
        # … comment omitted
        self.name = name
        self.data = []  # … comment omitted
    
    def public_method(self) -> str:
        # … docstring omitted
        # … comment omitted
        return self.name
    
    def _private_method(self):
        # … docstring omitted
        # … 3 comments omitted
        temp = self.name.upper()
        return temp  # … comment omitted
    
    # … comment omitted
    def method_with_lots_of_comments(self):
        # … comment omitted
        value = "test"
        
        # … 2 comments omitted
        processed = value.strip()
        
        # … comment omitted
        if not processed:
            # … comment omitted
            return None
            
        # … 2 comments omitted
        return processed.lower()

def standalone_function():
    # … docstring omitted
    # … comment omitted
    pass

# … comment omitted
def undocumented_function():
    # … 2 comments omitted
    x = 1  # … comment omitted
    y = 2  # … comment omitted
    return x + y  # … comment omitted

# … comment omitted
def function_with_annotations():
    # … docstring omitted
    # … comment omitted
    result = "placeholder"
    # … comment omitted
    return result

if __name__ == "__main__":
    # … comment omitted
    obj = CommentedClass("test")
    print(obj.public_method())

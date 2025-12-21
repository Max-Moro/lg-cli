"""Module docstring."""

import os
import sys
from typing import List, Optional

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.history = []
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        # … method body truncated
        return result
    
    def multiply(self, a: int, b: int) -> int:
        # Multiply two numbers
        result = a * b
        # … method body truncated
        return result
    
    def get_history(self) -> List[str]:
        return self.history.copy() # Get calculation history

def main():
    """Main function."""
    calc = Calculator("test")
    print(calc.add(2, 3))
    # … function body truncated
    
if __name__ == "__main__":
    main()

"""Module docstring."""

import os
import sys
from typing import List, Optional

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, name: str = "default"):
        """Initialize calculator."""
        self.name = name
        self.history = []
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result
    
    def get_history(self) -> List[str]:
        """Get calculation history."""
        return self.history.copy()

def main():
    """Main function."""
    calc = Calculator("test")
    print(calc.add(2, 3))
    print(calc.multiply(4, 5))
    
if __name__ == "__main__":
    main()

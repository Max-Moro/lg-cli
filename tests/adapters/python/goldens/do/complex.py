"""Complex test module combining multiple optimization types.

This module is designed to test multiple optimizations without
them interfering with each other. Each optimization should have
clear, non-overlapping effects.
"""

# Mixed imports for import optimization
import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np  # External library
from .utils import helper_function  # Local import

# Long import list for summarization testing
from collections import (
    defaultdict, Counter, deque, OrderedDict,
    ChainMap, UserDict, UserList, UserString
)

@dataclass
class DataModel:
    """Simple data model class."""
    name: str
    value: int
    metadata: Optional[Dict] = None

class ComplexOptimizationDemo:
    """Class demonstrating multiple optimization types.
    
    This class is designed so different optimizations
    can work on separate parts without interference.
    """
    
    # Class-level literals (literal optimization target)
    DEFAULT_CONFIG = {
        "timeout": 30,
        "retries": 3,
        "endpoints": [
            "/api/v1/users", "/api/v1/posts", "/api/v1/comments",
            "/api/v1/categories", "/api/v1/tags", "/api/v1/settings"
        ],
        "features": {
            "caching": True,
            "logging": True,
            "monitoring": False,
            "analytics": True
        }
    }
    
    LARGE_DATA_SET = [
        f"item_{i:03d}" for i in range(1, 31)  # 30 items for literal trimming
    ]
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        """Trivial constructor for field optimization.
        
        This constructor only does simple field assignments
        and should be targeted by field optimization.
        """
        # Simple field assignments (field optimization target)
        self.name = name
        self.config = config or {}
        self.data = []
        self.initialized = True
    
    def public_method_with_body(self, data: List[str]) -> Dict[str, int]:
        """Public method with substantial body for function body optimization.
        
        This method has enough logic to be worth stripping the body
        while preserving the signature and docstring.
        """
        # Comment that should be handled by comment optimization
        result = {}
        
        # Processing loop
        for item in data:
            if item not in result:
                result[item] = 0
            result[item] += 1
        
        # TODO: Consider using Counter instead
        # Additional processing
        total = sum(result.values())
        result["_total"] = total
        
        return result
    
    def _private_method_with_body(self) -> str:
        """Private method that should be filtered by public API optimization.
        
        This method should be removed entirely when public_api_only is enabled,
        so function body optimization won't have a chance to process it.
        """
        # Private implementation details
        temp = self.name.upper()
        processed = temp.replace(" ", "_")
        return f"private_{processed}"
    
    # Property accessors for field optimization
    @property
    def simple_name(self) -> str:
        """Trivial getter for field optimization."""
        return self.name
    
    @simple_name.setter
    def simple_name(self, value: str) -> None:
        """Trivial setter for field optimization."""
        self.name = value
    
    def process_with_comments_and_literals(self) -> Dict:
        """Method with various comment types and literal data.
        
        This method combines comment optimization targets
        with literal optimization targets.
        """
        # Regular comment for comment optimization
        config = {
            "processing_options": {
                "method": "standard",
                "validation": True,
                "error_handling": "strict",
                "logging_level": "INFO",
                "output_format": "json",
                "compression": False
            },
            "data_sources": [
                "database", "file_system", "api_endpoint",
                "cache", "memory", "external_service"
            ]
        }  # Large literal for literal optimization
        
        # FIXME: This needs better error handling
        # TODO: Add validation for config
        
        long_message = """This is a very long message that contains detailed information about the processing operation. It includes multiple sentences and provides comprehensive details that might not be essential for understanding the basic code structure."""  # String literal for trimming
        
        return {"config": config, "message": long_message}

# Public function for function body optimization (won't be filtered by public API)
def public_utility_function(items: List[DataModel]) -> Dict[str, List]:
    """Public utility function with processing logic.
    
    This function should keep its signature and docstring
    but have its body optimized by function body optimization.
    """
    # Comment that can be optimized
    categorized = {"valid": [], "invalid": []}
    
    # Processing logic
    for item in items:
        if item.value > 0:
            categorized["valid"].append(item)
        else:
            categorized["invalid"].append(item)
    
    # TODO: Add more sophisticated validation
    return categorized

def _private_utility_function() -> None:
    """Private function for public API filtering.
    
    This entire function should be removed by public API optimization.
    """
    # This won't be processed by other optimizations
    # because the whole function will be removed
    data = ["private", "implementation", "details"]
    return data

# Module-level function that's short (won't trigger function body optimization)
def simple_helper() -> str:
    """Simple one-liner function."""
    return "helper"  # Should be preserved due to size

if __name__ == "__main__":
    # Module execution block (should be preserved by public API optimization)
    demo = ComplexOptimizationDemo("test", {"debug": True})
    result = demo.public_method_with_body(["a", "b", "a"])
    print(f"Result: {result}")
    
    # Some comments for comment optimization in main block
    # TODO: Add more comprehensive testing
    models = [DataModel("item1", 1), DataModel("item2", -1)]
    processed = public_utility_function(models)
    print(f"Processed: {processed}")

"""Module for testing literal data optimization."""

import json

# Short string literal (should be preserved)
SHORT_STRING = "hello"

# Long string literal (candidate for trimming)
LONG_STRING = """This is a very long string that…""" """ literal string (−53 tokens) """

# Multi-line string with data
DATA_STRING = """
{
    "users": […""" # literal string (−114 tokens)

class DataContainer:
    """Class with various literal types."""
    
    def __init__(self):
        # Small array (should be preserved)
        self.small_list = [1, 2, 3]
        
        # Large array (candidate for trimming)
        self.large_list = [
    "item_1",
    "item_2", "…",
] # literal array (−116 tokens)
        
        # Small dictionary (should be preserved)
        self.small_dict = {"name": "test", "value": 42, "…": "…"} """ literal object (−-6 tokens) """
        
        # Large dictionary (candidate for trimming)
        self.large_dict = {
    "user_id": 12345,
    "…": "…",
} # literal object (−230 tokens)

def process_data():
    """Function with various literal data."""
    # Multi-line list
    categories = [
    "Technology",
    "Science",
    "Health", "…",
] # literal array (−39 tokens)
    
    # Nested data structure
    config = {
    "…": "…",
} # literal object (−157 tokens)
    
    # Very long single-line string
    sql_query = "SELECT users.id, users.username, users…" """ literal string (−66 tokens) """
    
    return categories, config, sql_query

# Set literal
TAGS = [
    , "…",
] # literal array (−46 tokens)

# Tuple with many elements
COORDINATES = (
    (0, 0), "…",
) # literal tuple (−64 tokens)

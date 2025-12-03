"""Module for testing literal data optimization."""

import json

# Short string literal (should be preserved)
SHORT_STRING = "hello"

# Long string literal (candidate for trimming)
LONG_STRING = """This is a very long string that contains a lot of text and might be a candidate for trimming when op…""" # literal string (−42 tokens)

# Multi-line string with data
DATA_STRING = """
{
    "users": [
        {"id": 1, "name":…""" # literal string (−105 tokens)

class DataContainer:
    """Class with various literal types."""
    
    def __init__(self):
        # Small array (should be preserved)
        self.small_list = [1, 2, 3]
        
        # Large array (candidate for trimming)
        self.large_list = [
            "item_1",
            "…",
        ] # literal array (−120 tokens)
        
        # Small dictionary (should be preserved)
        self.small_dict = {"name": "test", "value": 42}
        
        # Large dictionary (candidate for trimming)
        self.large_dict = {
            "user_id": 12345,
            # … (13 more, −220 tokens)
        }

def process_data():
    """Function with various literal data."""
    # Multi-line list
    categories = [
        "Technology",
        "Science",
        "…",
    ] # literal array (−44 tokens)
    
    # Nested data structure
    config = {
        "database": {
            "host": "localhost",
            # … (3 more, −38 tokens)
        },
        # … (2 more, −142 tokens)
    }
    
    # Very long single-line string
    sql_query = "SELECT users.id, users.username, users.email, profiles.first_name, profiles.last_name, pro…" # literal string (−57 tokens)
    
    return categories, config, sql_query

# Set literal
TAGS = {
    "python",
    "javascript",
    "…",
} # literal set (−39 tokens)

# Tuple with many elements
COORDINATES = (
    (0, 0),
    "…",
) # literal tuple (−66 tokens)

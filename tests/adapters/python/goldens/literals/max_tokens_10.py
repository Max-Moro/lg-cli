"""Module for testing literal data optimization."""

import json

# Short string literal (should be preserved)
SHORT_STRING = "hello"

# Long string literal (candidate for trimming)
LONG_STRING = """This is a very long string that contains…""" # literal string (−55 tokens)

# Multi-line string with data
DATA_STRING = """
{
    "user…""" # literal string (−117 tokens)

class DataContainer:
    """Class with various literal types."""
    
    def __init__(self):
        # Small array (should be preserved)
        self.small_list = [1, 2, 3]
        
        # Large array (candidate for trimming)
        self.large_list = [
            "item_1",
            "item_2",
            "…",
        ] # literal array (−115 tokens)
        
        # Small dictionary (should be preserved)
        self.small_dict = {"name": "test", "value": 42}
        
        # Large dictionary (candidate for trimming)
        self.large_dict = {
            "user_id": 12345,
            "is_active": True,
            # … (12 more, −216 tokens)
        }

def process_data():
    """Function with various literal data."""
    # Multi-line list
    categories = [
        "Technology",
        "Science",
        "Health",
        "…",
    ] # literal array (−41 tokens)
    
    # Nested data structure
    config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "myapp",
            "credentials": {
                "username": "admin",
                "password": "super_secret_password_123456789"
            }
        },
        # … (2 more, −104 tokens)
    }
    
    # Very long single-line string
    sql_query = "SELECT users.id, users.username, users.e…" # literal string (−67 tokens)
    
    return categories, config, sql_query

# Set literal
TAGS = {
    "python",
    "javascript",
    "typescript",
    "…",
} # literal set (−36 tokens)

# Tuple with many elements
COORDINATES = (
    (0, 0),
    "…",
) # literal tuple (−66 tokens)

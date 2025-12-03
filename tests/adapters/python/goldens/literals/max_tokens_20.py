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
        "Education",
        "…",
    ] # literal array (−38 tokens)
    
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
    sql_query = "SELECT users.id, users.username, users.email, profiles.first_name, profiles.last_name, pro…" # literal string (−57 tokens)
    
    return categories, config, sql_query

# Set literal
TAGS = {
    "python",
    "javascript",
    "typescript",
    "java",
    "…",
} # literal set (−33 tokens)

# Tuple with many elements
COORDINATES = (
    (0, 0),
    (1, 1),
    "…",
) # literal tuple (−60 tokens)

"""Module for testing literal data optimization."""

import json

# Short string literal (should be preserved)
SHORT_STRING = "hello"

# Long string literal (candidate for trimming)
LONG_STRING = """This is a very long string...""" # … literal string (−54 tokens)

# Multi-line string with data
DATA_STRING = """
{
    "users":...""" # … literal string (−114 tokens)

class DataContainer:
    """Class with various literal types."""
    
    def __init__(self):
        # Small array (should be preserved)
        self.small_list = [1, 2, 3]
        
        # Large array (candidate for trimming)
        self.large_list = [
            "item_1",...] # … literal array (−125 tokens)
        
        # Small dictionary (should be preserved)
        self.small_dict = {"name": "test", "value...} # … literal object (−2 tokens)
        
        # Large dictionary (candidate for trimming)
        self.large_dict = {
            "user_id":...} # … literal object (−240 tokens)

def process_data():
    """Function with various literal data."""
    # Multi-line list
    categories = [
        "Technology", "Science"...] # … literal array (−47 tokens)
    
    # Nested data structure
    config = {
        "database":...} # … literal object (−159 tokens)
    
    # Very long single-line string
    sql_query = "SELECT users.id, users.username,..." # … literal string (−67 tokens)
    
    return categories, config, sql_query

# Set literal
TAGS = [{
    "python", "javascript"...] # … literal array (−43 tokens)

# Tuple with many elements
COORDINATES = (
    (0, 0),...) # … literal tuple (−67 tokens)

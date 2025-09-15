"""Module for testing literal data optimization."""

import json

# Short string literal (should be preserved)
SHORT_STRING = "hello"

# Long string literal (candidate for trimming)
LONG_STRING = """This is a very long string that contains a lot of text and might be a candidate for trimming when optimizing code for AI context windows. It has multiple sentences and provides detailed explanations that might not be essential for understanding the code structure. This string continues with even more verbose content to ensure it exceeds typical trimming thresholds."""

# Multi-line string with data
DATA_STRING = """
{
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ],
    "metadata": {
        "version": "1.0",
        "timestamp": "2024-01-15T10:30:00Z",
        "description": "Sample user data for testing purposes"
    }
}
"""

class DataContainer:
    """Class with various literal types."""
    
    def __init__(self):
        # Small array (should be preserved)
        self.small_list = [1, 2, 3]
        
        # Large array (candidate for trimming)
        self.large_list = [
            "item_1", "item_2", "item_3", "item_4", "item_5",
            "item_6", "item_7", "item_8", "item_9", "item_10",
            "item_11", "item_12", "item_13", "item_14", "item_15",
            "item_16", "item_17", "item_18", "item_19", "item_20",
            "item_21", "item_22", "item_23", "item_24", "item_25"
        ]
        
        # Small dictionary (should be preserved)
        self.small_dict = {"name": "test", "value": 42}
        
        # Large dictionary (candidate for trimming)
        self.large_dict = {
            "user_id": 12345,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "12345",
                "country": "USA"
            },
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True,
                "newsletter": False
            },
            "roles": ["user", "beta_tester", "premium"],
            "last_login": "2024-01-15T10:30:00Z",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "is_active": True,
            "settings": {
                "privacy": "public",
                "two_factor": True,
                "session_timeout": 3600
            }
        }

def process_data():
    """Function with various literal data."""
    # Multi-line list
    categories = [
        "Technology", "Science", "Health", "Education", "Entertainment",
        "Sports", "Travel", "Food", "Fashion", "Business", "Politics",
        "Environment", "Art", "Music", "Literature", "History"
    ]
    
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
        "api": {
            "endpoints": [
                "/api/v1/users",
                "/api/v1/posts", 
                "/api/v1/comments",
                "/api/v1/categories",
                "/api/v1/tags"
            ],
            "rate_limit": 1000,
            "timeout": 30
        },
        "features": {
            "authentication": True,
            "caching": True,
            "logging": True,
            "monitoring": True,
            "compression": False
        }
    }
    
    # Very long single-line string
    sql_query = "SELECT users.id, users.username, users.email, profiles.first_name, profiles.last_name, profiles.bio, addresses.street, addresses.city, addresses.state, addresses.zip_code FROM users JOIN profiles ON users.id = profiles.user_id JOIN addresses ON users.id = addresses.user_id WHERE users.is_active = true AND profiles.is_public = true ORDER BY users.created_at DESC LIMIT 100"
    
    return categories, config, sql_query

# Set literal
TAGS = {
    "python", "javascript", "typescript", "java", "csharp", "cpp", "rust",
    "go", "kotlin", "swift", "php", "ruby", "scala", "clojure", "haskell"
}

# Tuple with many elements
COORDINATES = (
    (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5),
    (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11)
)

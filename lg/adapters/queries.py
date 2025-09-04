"""
Tree-sitter query definitions for different programming languages.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

# ====================== PYTHON QUERIES =======================

PYTHON_QUERIES = {
    # Functions and methods
    "functions": """
    (function_definition
      name: (identifier) @function_name
      body: (block) @function_body)
    """,
    
    "methods": """
    (class_definition
      body: (block
        (function_definition
          name: (identifier) @method_name
          body: (block) @method_body)))
    """,
    
    # Comments and docstrings  
    "comments": """
    (comment) @comment
    
    (expression_statement
      (string) @docstring)
    """,
    
    # Import statements
    "imports": """
    (import_statement) @import_statement
      
    (import_from_statement) @import_from
    """,
    
    # Class definitions
    "classes": """
    (class_definition
      name: (identifier) @class_name
      body: (block) @class_body)
    """,
    
    # Variable assignments
    "assignments": """
    (assignment
      left: (identifier) @variable_name
      right: (_) @variable_value)
    """,
}

# ====================== TYPESCRIPT QUERIES =======================

TYPESCRIPT_QUERIES = {
    # Functions and methods
    "functions": """
    (function_declaration
      name: (identifier) @function_name
      body: (statement_block) @function_body)
      
    (method_definition
      name: (property_identifier) @method_name  
      body: (statement_block) @method_body)
      
    (arrow_function
      body: (_) @arrow_function_body)
    """,
    
    "methods": """
    (class_declaration
      body: (class_body
        (method_definition
          name: (property_identifier) @method_name
          body: (statement_block) @method_body)))
    """,
    
    # Comments
    "comments": """
    (comment) @comment
    """,
    
    # Import statements
    "imports": """
    (import_statement) @import
    """,
    
    # Class definitions  
    "classes": """
    (class_declaration
      name: (type_identifier) @class_name
      body: (class_body) @class_body)
    """,
    
    # Interface definitions
    "interfaces": """
    (interface_declaration
      name: (type_identifier) @interface_name
      body: (object_type) @interface_body)
    """,
    
    # Variable declarations
    "variables": """
    (variable_declaration
      (variable_declarator
        name: (identifier) @variable_name
        value: (_)? @variable_value))
    """,
    
    # Export statements
    "exports": """
    (export_statement) @export
    """,
}

# ====================== JAVASCRIPT QUERIES =======================
# JavaScript uses the same queries as TypeScript for most constructs
JAVASCRIPT_QUERIES = TYPESCRIPT_QUERIES.copy()

# Remove TypeScript-specific queries for JavaScript
JAVASCRIPT_QUERIES.update({
    "interfaces": """
    ; JavaScript doesn't have interfaces
    """,
})

# ====================== HELPER FUNCTIONS =======================

def get_queries_for_language(language: str) -> dict[str, str]:
    """
    Get query definitions for a specific language.
    
    Args:
        language: Language name ('python', 'typescript', 'javascript')
        
    Returns:
        Dictionary of query definitions
        
    Raises:
        ValueError: If language is not supported
    """
    query_map = {
        'python': PYTHON_QUERIES,
        'typescript': TYPESCRIPT_QUERIES,
        'javascript': JAVASCRIPT_QUERIES,
    }
    
    if language not in query_map:
        raise ValueError(f"Unsupported language: {language}. Supported: {list(query_map.keys())}")
    
    return query_map[language]

def validate_query_syntax(query_string: str) -> bool:
    """
    Basic validation of query syntax.
    
    Args:
        query_string: Tree-sitter query string
        
    Returns:
        True if syntax appears valid
    """
    # Basic S-expression validation
    if not query_string.strip():
        return False
        
    # Count parentheses
    open_count = query_string.count('(')
    close_count = query_string.count(')')
    
    return open_count == close_count

def get_capture_names(query_string: str) -> list[str]:
    """
    Extract capture names from a query string.
    
    Args:
        query_string: Tree-sitter query string
        
    Returns:
        List of capture names (without @ prefix)
    """
    import re
    captures = re.findall(r'@(\w+)', query_string)
    return list(set(captures))

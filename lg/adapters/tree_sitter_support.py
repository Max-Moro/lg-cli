"""
Tree-sitter infrastructure for language adapters.
Provides grammar loading, query management, and utilities for AST parsing.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any

try:
    import tree_sitter
    from tree_sitter import Language, Tree, Node, Parser
    # Прямые импорты языковых модулей
    import tree_sitter_python
    import tree_sitter_typescript  
    import tree_sitter_javascript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    # Stub classes for type hints when tree-sitter is not available
    class Language:
        pass
    class Tree:
        pass
    class Node:
        pass
    class Parser:
        pass


class TreeSitterError(Exception):
    """Base exception for Tree-sitter related errors."""
    pass


class GrammarNotFoundError(TreeSitterError):
    """Raised when requested grammar is not available."""
    pass


# Language name mappings to tree-sitter modules with their language functions
LANGUAGE_MODULES = {
    "python": (tree_sitter_python, "language") if TREE_SITTER_AVAILABLE else None,
    "typescript": (tree_sitter_typescript, "language_typescript") if TREE_SITTER_AVAILABLE else None,
    "javascript": (tree_sitter_javascript, "language") if TREE_SITTER_AVAILABLE else None,
    # TODO: Add more languages when modules are installed
    # "java": tree_sitter_java,
    # "cpp": tree_sitter_cpp,
    # "c": tree_sitter_c,
    # "scala": tree_sitter_scala,
}


@lru_cache(maxsize=10)
def get_language_parser(lang_name: str) -> Tuple[Language, Parser]:
    """
    Get cached language and parser for the given language.
    
    Args:
        lang_name: Language name (python, typescript, etc.)
        
    Returns:
        Tuple of (Language, Parser)
        
    Raises:
        GrammarNotFoundError: If language is not supported
        TreeSitterError: If tree-sitter is not available
    """
    if not TREE_SITTER_AVAILABLE:
        raise TreeSitterError("tree-sitter is not available. Install with: pip install tree-sitter tree-sitter-python tree-sitter-typescript tree-sitter-javascript")
    
    language_info = LANGUAGE_MODULES.get(lang_name)
    if not language_info:
        raise GrammarNotFoundError(f"Language '{lang_name}' is not supported or module not installed")
    
    try:
        # Распаковываем модуль и функцию
        language_module, language_func_name = language_info
        
        # Получаем язык из модуля (PyCapsule)
        language_func = getattr(language_module, language_func_name)
        language_capsule = language_func()
        
        # Создаем Language объект из capsule
        language = Language(language_capsule)
        
        # Создаем парсер
        parser = Parser(language)
        
        return language, parser
    except Exception as e:
        raise GrammarNotFoundError(f"Failed to load language '{lang_name}': {e}")


class QueryRegistry:
    """Registry for Tree-sitter queries by language."""
    
    def __init__(self):
        self._queries: Dict[str, Dict[str, Any]] = {}
        self._compiled_queries: Dict[str, Any] = {}
    
    def register_query(self, lang_name: str, query_name: str, query_text: str) -> None:
        """Register a query for a language."""
        if lang_name not in self._queries:
            self._queries[lang_name] = {}
        self._queries[lang_name][query_name] = query_text
    
    @lru_cache(maxsize=50)
    def get_compiled_query(self, lang_name: str, query_name: str):
        """Get compiled query for language and query name."""
        if not TREE_SITTER_AVAILABLE:
            raise TreeSitterError("tree-sitter is not available")
        
        cache_key = f"{lang_name}:{query_name}"
        if cache_key in self._compiled_queries:
            return self._compiled_queries[cache_key]
        
        if lang_name not in self._queries or query_name not in self._queries[lang_name]:
            raise ValueError(f"Query '{query_name}' not found for language '{lang_name}'")
        
        language, _ = get_language_parser(lang_name)
        query_text = self._queries[lang_name][query_name]
        
        try:
            # Используем новый API Query constructor
            from tree_sitter import Query
            compiled_query = Query(language, query_text)
            self._compiled_queries[cache_key] = compiled_query
            return compiled_query
        except Exception as e:
            raise TreeSitterError(f"Failed to compile query '{query_name}' for '{lang_name}': {e}")
    
    def list_queries(self, lang_name: str) -> List[str]:
        """List available queries for a language."""
        return list(self._queries.get(lang_name, {}).keys())


# Global query registry
query_registry = QueryRegistry()


def register_default_queries():
    """Register default queries for supported languages."""
    
    # Python queries
    query_registry.register_query("python", "functions", """
    (function_definition
      name: (identifier) @function_name
      parameters: (parameters) @function_params
      body: (block) @function_body) @function_def
    """)
    
    query_registry.register_query("python", "methods", """
    (class_definition
      body: (block
        (function_definition
          name: (identifier) @method_name
          parameters: (parameters) @method_params
          body: (block) @method_body) @method_def))
    """)
    
    query_registry.register_query("python", "classes", """
    (class_definition
      name: (identifier) @class_name
      body: (block) @class_body) @class_def
    """)
    
    query_registry.register_query("python", "imports", """
    (import_statement) @import
    (import_from_statement) @import_from
    """)
    
    # TypeScript/JavaScript queries
    for lang in ["typescript", "javascript"]:
        query_registry.register_query(lang, "functions", """
        (function_declaration
          name: (identifier) @function_name
          parameters: (formal_parameters) @function_params
          body: (statement_block) @function_body) @function_def
        
        (arrow_function
          parameters: (formal_parameters) @arrow_params
          body: (_) @arrow_body) @arrow_function
        
        (function_expression
          name: (identifier)? @expr_name
          parameters: (formal_parameters) @expr_params
          body: (statement_block) @expr_body) @function_expr
        """)
        
        query_registry.register_query(lang, "methods", """
        (method_definition
          name: (_) @method_name
          parameters: (formal_parameters) @method_params
          body: (statement_block) @method_body) @method_def
        """)
        
        query_registry.register_query(lang, "classes", """
        (class_declaration
          name: (identifier) @class_name
          body: (class_body) @class_body) @class_def
        """)
        
        query_registry.register_query(lang, "imports", """
        (import_statement) @import
        """)
    
    # Add TypeScript-specific queries
    query_registry.register_query("typescript", "interfaces", """
    (interface_declaration
      name: (type_identifier) @interface_name
      body: (object_type) @interface_body) @interface_def
    """)
    
    query_registry.register_query("typescript", "type_aliases", """
    (type_alias_declaration
      name: (type_identifier) @type_name
      value: (_) @type_value) @type_def
    """)


class TreeSitterDocument:
    """Wrapper for Tree-sitter parsed document."""
    
    def __init__(self, text: str, lang_name: str):
        self.text = text
        self.lang_name = lang_name
        self.tree: Optional[Tree] = None
        self._parse()
    
    def _parse(self):
        """Parse the document with Tree-sitter."""
        if not TREE_SITTER_AVAILABLE:
            raise TreeSitterError("tree-sitter is not available")
        
        _, parser = get_language_parser(self.lang_name)
        self.tree = parser.parse(self.text.encode('utf-8'))
    
    @property
    def root_node(self) -> Node:
        """Get the root node of the parsed tree."""
        if not self.tree:
            raise TreeSitterError("Document not parsed")
        return self.tree.root_node
    
    def query(self, query_name: str) -> List[Tuple[Node, str]]:
        """
        Execute a named query on the document.
        
        Returns:
            List of (node, capture_name) tuples
        """
        if not self.tree:
            raise TreeSitterError("Document not parsed")
        
        # Для простоты используем manual traversal вместо queries
        # TODO: Исправить когда найдем правильный API для queries
        if query_name == "functions":
            return self._find_functions()
        elif query_name == "methods":
            return self._find_methods()
        else:
            # Fallback to empty results for now
            return []
    
    def _find_functions(self) -> List[Tuple[Node, str]]:
        """Find function definitions manually (only top-level and nested, not methods)."""
        results = []
        
        def traverse(node: Node, in_class: bool = False):
            # Python functions
            if node.type == "function_definition" and not in_class:
                results.append((node, "function_def"))
                # Find function body
                for child in node.children:
                    if child.type == "block":
                        results.append((child, "function_body"))
                        break
            
            # TypeScript/JavaScript functions
            elif node.type == "function_declaration" and not in_class:
                results.append((node, "function_def"))
                # Find function body
                for child in node.children:
                    if child.type == "statement_block":
                        results.append((child, "function_body"))
                        break
            
            # Arrow functions (TypeScript/JavaScript)
            elif node.type == "arrow_function" and not in_class:
                results.append((node, "function_def"))
                # Arrow function body might be block or expression
                for child in node.children:
                    if child.type in ("statement_block", "expression"):
                        results.append((child, "function_body"))
                        break
            
            # Don't traverse into class definitions for functions
            if node.type in ("class_definition", "class_declaration"):
                return  # Skip class content for top-level functions
                
            for child in node.children:
                traverse(child, in_class)
        
        traverse(self.root_node)
        return results
    
    def _find_methods(self) -> List[Tuple[Node, str]]:
        """Find method definitions in classes manually."""
        results = []
        
        def traverse(node: Node):
            # Python classes
            if node.type == "class_definition":
                # Look for methods inside Python class
                for class_child in node.children:
                    if class_child.type == "block":
                        for method_node in class_child.children:
                            if method_node.type == "function_definition":
                                results.append((method_node, "method_def"))
                                # Find method body
                                for child in method_node.children:
                                    if child.type == "block":
                                        results.append((child, "method_body"))
                                        break
            
            # TypeScript/JavaScript classes
            elif node.type == "class_declaration":
                # Look for methods inside TypeScript class
                for class_child in node.children:
                    if class_child.type == "class_body":
                        for method_node in class_child.children:
                            if method_node.type == "method_definition":
                                results.append((method_node, "method_def"))
                                # Find method body
                                for child in method_node.children:
                                    if child.type == "statement_block":
                                        results.append((child, "method_body"))
                                        break
            
            for child in node.children:
                traverse(child)
        
        traverse(self.root_node)
        return results
    
    def get_node_text(self, node: Node) -> str:
        """Get text content for a node."""
        start_byte = node.start_byte
        end_byte = node.end_byte
        return self.text.encode('utf-8')[start_byte:end_byte].decode('utf-8')
    
    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """Get byte range for a node."""
        return node.start_byte, node.end_byte
    
    def get_line_range(self, node: Node) -> Tuple[int, int]:
        """Get line range (0-based) for a node."""
        return node.start_point[0], node.end_point[0]


def create_document(text: str, lang_name: str) -> TreeSitterDocument:
    """Create a parsed Tree-sitter document."""
    return TreeSitterDocument(text, lang_name)


def is_tree_sitter_available() -> bool:
    """Check if Tree-sitter is available."""
    return TREE_SITTER_AVAILABLE


def get_supported_languages() -> List[str]:
    """Get list of supported languages."""
    return [lang for lang, lang_info in LANGUAGE_MODULES.items() if lang_info is not None]


# Initialize default queries when module is imported
if TREE_SITTER_AVAILABLE:
    register_default_queries()

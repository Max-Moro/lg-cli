"""
Field optimization.
Processes trivial constructors, getters, and setters according to configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, cast

from ..context import ProcessingContext
from ..tree_sitter_support import Node, TreeSitterDocument


class FieldsClassifier(ABC):
    """Abstract base class for fields classification."""
    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc

    @abstractmethod
    def is_trivial_constructor(self, constructor_body: Node) -> bool:
        """Определяет, является ли конструктор тривиальным."""
        pass

    @abstractmethod
    def is_trivial_getter(self, getter_body: Node) -> bool:
        """Определяет, является ли геттер тривиальным."""
        pass

    @abstractmethod
    def is_trivial_setter(self, setter_body: Node) -> bool:
        """Определяет, является ли сеттер тривиальным."""
        pass


class FieldOptimizer:
    """Handles field-related optimization (constructors, getters, setters)."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply field optimization based on configuration.
        
        Args:
            context: Processing context with document and editor
        """
        config = self.adapter.cfg.fields

        classifier: Optional[FieldsClassifier] = None
        if config.strip_trivial_constructors or config.strip_trivial_accessors:
            classifier = self.adapter.create_fields_classifier(context.doc)
        
        # Apply trivial constructor optimization
        if config.strip_trivial_constructors:
            self._process_trivial_constructors(context, classifier)
        
        # Apply trivial accessor optimization  
        if config.strip_trivial_accessors:
            self._process_trivial_accessors(context, classifier)
    
    def _process_trivial_constructors(self, context: ProcessingContext, classifier: FieldsClassifier) -> None:
        """
        Process and strip trivial constructors.
        
        Args:
            context: Processing context
        """
        # Find constructors using language-specific queries
        constructors = context.doc.query("constructors")
        
        for node, capture_name in constructors:
            if capture_name == "constructor_body":
                # Check if constructor is trivial
                is_trivial = classifier.is_trivial_constructor(node)

                if is_trivial:
                    self._strip_constructor_body(node, context)
    
    def _process_trivial_accessors(self, context: ProcessingContext, classifier: FieldsClassifier) -> None:
        """
        Process and strip trivial getters and setters.
        
        Args:
            context: Processing context
        """
        # Process property getters and setters (Python @property, TypeScript get/set)
        self._process_property_accessors(context, classifier)
        
        # Process simple getters and setters (get_/set_ methods)
        self._process_simple_accessors(context, classifier)
    
    def _process_property_accessors(self, context: ProcessingContext, classifier: FieldsClassifier) -> None:
        """Process @property or get/set methods."""
        # Process getters
        getters = context.doc.query_opt("getters")
        properties = context.doc.query_opt("properties")
        
        # Combine Python @property and TypeScript get methods
        all_getters = list(getters) + list(properties)
        
        for node, capture_name in all_getters:
            if capture_name in ("getter_body", "property_body"):
                is_trivial = classifier.is_trivial_getter(node)

                if is_trivial:
                    self._strip_getter_body(node, context)
        
        # Process setters
        setters = context.doc.query_opt("setters")
        
        for node, capture_name in setters:
            if capture_name in ("setter_body",):
                is_trivial = classifier.is_trivial_setter(node)

                if is_trivial:
                    self._strip_setter_body(node, context)
    
    def _process_simple_accessors(self, context: ProcessingContext, classifier: FieldsClassifier) -> None:
        """Process simple get_/set_ methods."""
        simple_accessors = context.doc.query_opt("simple_getters_setters")
        
        for node, capture_name in simple_accessors:
            if capture_name == "method_body":
                # Get method name to determine if it's getter or setter
                method_name = self._get_method_name(node, context.doc)
                
                if method_name and method_name.startswith(("get_", "get")):
                    # Simple getter
                    is_trivial = classifier.is_trivial_getter(node)

                    if is_trivial:
                        self._strip_getter_body(node, context)
                
                elif method_name and method_name.startswith(("set_", "set")):
                    # Simple setter
                    is_trivial = classifier.is_trivial_setter(node)

                    if is_trivial:
                        self._strip_setter_body(node, context)
    
    def _strip_constructor_body(self, body_node, context: ProcessingContext) -> None:
        """Strip trivial constructor body."""
        # Используем новое простое API с кастомным типом
        start_byte, end_byte = context.doc.get_node_range(body_node)
        start_line, end_line = context.doc.get_line_range(body_node)
        
        context.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line,
            placeholder_type="constructor"
        )
        
        # Update metrics
        context.metrics.increment("code.removed.constructors")
    
    def _strip_getter_body(self, body_node, context: ProcessingContext) -> None:
        """Strip trivial getter body."""
        start_byte, end_byte = context.doc.get_node_range(body_node)
        start_line, end_line = context.doc.get_line_range(body_node)
        
        context.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line,
            placeholder_type="getter"
        )
        
        # Update metrics
        context.metrics.increment("code.removed.getters")
    
    def _strip_setter_body(self, body_node, context: ProcessingContext) -> None:
        """Strip trivial setter body."""
        start_byte, end_byte = context.doc.get_node_range(body_node)
        start_line, end_line = context.doc.get_line_range(body_node)
        
        context.add_custom_placeholder(
            start_byte, end_byte, start_line, end_line,
            placeholder_type="setter"
        )
        
        # Update metrics
        context.metrics.increment("code.removed.setters")
    
    @staticmethod
    def _get_method_name(body_node, doc: TreeSitterDocument) -> str:
        """
        Get method name for a method body node.
        
        Args:
            body_node: Method body node
            doc: Tree-sitter документ
            
        Returns:
            Method name or empty string if not found
        """
        # Walk up to find the method definition
        current = body_node.parent
        while current:
            if current.type in ("function_definition", "method_definition"):
                # Find name node
                for child in current.children:
                    if child.type in ("identifier", "property_identifier"):
                        return doc.get_node_text(child)
                break
            current = current.parent
        
        return ""

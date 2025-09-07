"""Module for testing field optimization (constructors, getters, setters)."""

from typing import Optional, List

class TrivialConstructorClass:
    """Class with trivial constructor for testing."""
    
    def __init__(self, name: str, age: int, email: str):
        """Trivial constructor - only simple field assignments."""
        super().__init__()
        self.name = name
        self.age = age
        self.email = email
        self.created_at = None

class NonTrivialConstructorClass:
    """Class with non-trivial constructor."""
    
    def __init__(self, data: dict):
        """Non-trivial constructor with validation and processing."""
        super().__init__()
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        # Complex initialization logic
        self.name = data.get("name", "").strip().title()
        self.age = int(data.get("age", 0))
        if self.age < 0:
            raise ValueError("Age cannot be negative")
            
        self.email = self._validate_email(data.get("email", ""))
        self.metadata = self._process_metadata(data)
    
    def _validate_email(self, email: str) -> str:
        """Private email validation helper."""
        if "@" not in email:
            raise ValueError("Invalid email format")
        return email.lower()
    
    def _process_metadata(self, data: dict) -> dict:
        """Private metadata processing helper."""
        return {k: v for k, v in data.items() if k not in ["name", "age", "email"]}

class PropertyBasedClass:
    """Class with property-based getters and setters."""
    
    def __init__(self, initial_value: int = 0):
        """Initialize with backing field."""
        self._value = initial_value
        self._name = ""
        self._items = []
    
    @property
    def value(self) -> int:
        """Trivial getter - should be stripped."""
        return self._value
    
    @value.setter
    def value(self, new_value: int) -> None:
        """Trivial setter - should be stripped."""
        self._value = new_value
    
    @property
    def name(self) -> str:
        """Another trivial getter."""
        return self._name
    
    @name.setter  
    def name(self, new_name: str) -> None:
        """Another trivial setter."""
        self._name = new_name
    
    @property
    def computed_property(self) -> str:
        """Non-trivial getter with computation."""
        base = f"Value: {self._value}"
        if self._name:
            base += f", Name: {self._name}"
        return base.upper()
    
    @property
    def items(self) -> List[str]:
        """Trivial getter returning copy."""
        return self._items.copy()
    
    @items.setter
    def items(self, new_items: List[str]) -> None:
        """Non-trivial setter with validation."""
        if not isinstance(new_items, list):
            raise TypeError("Items must be a list")
        
        validated_items = []
        for item in new_items:
            if isinstance(item, str) and item.strip():
                validated_items.append(item.strip())
        
        self._items = validated_items

class SimpleAccessorClass:
    """Class with simple get_/set_ methods."""
    
    def __init__(self):
        self._data = {}
        self._count = 0
        self._status = "inactive"
    
    def get_data(self) -> dict:
        """Trivial getter method."""
        return self._data
    
    def set_data(self, data: dict) -> None:
        """Trivial setter method."""
        self._data = data
    
    def get_count(self) -> int:
        """Trivial getter for count."""
        return self._count
    
    def set_count(self, count: int) -> None:
        """Trivial setter for count."""
        self._count = count
    
    def get_status(self) -> str:
        """Trivial getter for status."""
        return self._status
    
    def set_status(self, status: str) -> None:
        """Non-trivial setter with validation."""
        valid_statuses = ["active", "inactive", "pending", "error"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        
        self._status = status
        self._log_status_change(status)
    
    def _log_status_change(self, new_status: str) -> None:
        """Private helper for logging."""
        print(f"Status changed to: {new_status}")

class MixedFieldClass:
    """Class mixing trivial and non-trivial field operations."""
    
    def __init__(self, name: str, config: Optional[dict] = None):
        """Mixed constructor - some trivial, some complex."""
        # Trivial assignments
        self.name = name
        self.id = None
        
        # Non-trivial initialization
        if config is None:
            config = self._default_config()
        
        self.config = self._validate_config(config)
        self.initialized = True
    
    def _default_config(self) -> dict:
        """Generate default configuration."""
        return {
            "debug": False,
            "timeout": 30,
            "retries": 3
        }
    
    def _validate_config(self, config: dict) -> dict:
        """Validate configuration."""
        required_keys = ["debug", "timeout", "retries"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        return config
    
    @property
    def display_name(self) -> str:
        """Trivial property getter."""
        return self.name
    
    @property
    def full_info(self) -> dict:
        """Non-trivial property with computation."""
        return {
            "name": self.name,
            "id": self.id,
            "config": self.config,
            "status": "initialized" if self.initialized else "pending"
        }

# Edge case: Empty constructor
class EmptyConstructorClass:
    """Class with empty constructor."""
    
    def __init__(self):
        """Empty constructor - should be considered trivial."""
        pass

# Edge case: Constructor with only super() call
class SuperOnlyConstructorClass:
    """Class with constructor that only calls super()."""
    
    def __init__(self):
        """Constructor with only super() call."""
        super().__init__()

# Edge case: Constructor with docstring only
class DocstringOnlyConstructorClass:
    """Class with constructor containing only docstring."""
    
    def __init__(self):
        """Constructor with detailed documentation.
        
        This constructor doesn't do anything except
        provide documentation. Should be considered trivial.
        """
        pass

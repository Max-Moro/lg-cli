"""Package with annotated __all__ declaration."""

from .module import func
from .other import Class

__all__: list[str] = ["func", "Class"]

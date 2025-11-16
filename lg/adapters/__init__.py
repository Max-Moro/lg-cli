from __future__ import annotations

# Public API of adapters package:
#  • process_files — file processing engine
#  • get_adapter_for_path — lazy retrieval of adapter class by path
from .processor import process_files
from .registry import get_adapter_for_path, register_lazy

__all__ = ["process_files", "get_adapter_for_path", "register_lazy"]

# ---- Lightweight (lazy) registration of built-in adapters --------------------
# No heavy module imports here — only module:class strings.
# The adapter module will be imported exactly at the moment of first request by extension.

# Tree-sitter based adapters
register_lazy(module=".python", class_name="PythonAdapter", extensions=[".py"])
register_lazy(module=".typescript", class_name="TypeScriptAdapter", extensions=[".ts", ".tsx"])
register_lazy(module=".kotlin", class_name="KotlinAdapter", extensions=[".kt", ".kts"])

# Markdown adapter
register_lazy(module=".markdown", class_name="MarkdownAdapter", extensions=[".md", ".markdown"])

# Stub adapters for future languages
# register_lazy(module=".javascript", class_name="JavaScriptAdapter", extensions=[".js", ".jsx"])
# register_lazy(module=".java", class_name="JavaAdapter", extensions=[".java"])
# register_lazy(module=".cpp", class_name="CppAdapter", extensions=[".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"])
# register_lazy(module=".scala", class_name="ScalaAdapter", extensions=[".scala"])

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
register_lazy(module=".langs/python", class_name="PythonAdapter", extensions=[".py"])
register_lazy(module=".langs/typescript", class_name="TypeScriptAdapter", extensions=[".ts", ".tsx"])
register_lazy(module=".langs/kotlin", class_name="KotlinAdapter", extensions=[".kt", ".kts"])
register_lazy(module=".langs/javascript", class_name="JavaScriptAdapter", extensions=[".js", ".jsx", ".mjs", ".cjs"])
register_lazy(module=".langs/java", class_name="JavaAdapter", extensions=[".java"])
register_lazy(module=".langs/cpp", class_name="CppAdapter", extensions=[".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"])
register_lazy(module=".langs/c", class_name="CAdapter", extensions=[".c", ".h"])
register_lazy(module=".langs/scala", class_name="ScalaAdapter", extensions=[".scala", ".sc"])
register_lazy(module=".langs/go", class_name="GoAdapter", extensions=[".go"])
register_lazy(module=".langs/rust", class_name="RustAdapter", extensions=[".rs"])

# Markdown adapter
register_lazy(module=".markdown", class_name="MarkdownAdapter", extensions=[".md", ".markdown"])

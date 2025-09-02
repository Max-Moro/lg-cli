from __future__ import annotations

# Публичный API пакета adapters:
#  • process_groups — движок обработки
#  • get_adapter_for_path — ленивое получение класса адаптера по пути
from .engine import process_groups
from .registry import get_adapter_for_path, register_lazy

__all__ = ["process_groups", "get_adapter_for_path", "register_lazy"]

# ---- Лёгкая (ленивая) регистрация встроенных адаптеров --------------------
# Никаких импортов тяжёлых модулей здесь нет — только строки module:class.
# Модуль адаптера будет импортирован ровно в момент первого запроса по расширению.

# Tree-sitter based adapters (M1 implementation)
register_lazy(module=".python_tree_sitter", class_name="PythonTreeSitterAdapter", extensions=[".py"])
register_lazy(module=".typescript_tree_sitter", class_name="TypeScriptTreeSitterAdapter", extensions=[".ts", ".tsx"])
register_lazy(module=".typescript_tree_sitter", class_name="JavaScriptTreeSitterAdapter", extensions=[".js", ".jsx"])

# Markdown adapter
register_lazy(module=".markdown", class_name="MarkdownAdapter", extensions=[".md", ".markdown"])

# Stub adapters for future languages (M7 implementation)
register_lazy(module=".java", class_name="JavaAdapter", extensions=[".java"])
register_lazy(module=".cpp", class_name="CppAdapter", extensions=[".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"])
register_lazy(module=".scala", class_name="ScalaAdapter", extensions=[".scala"])

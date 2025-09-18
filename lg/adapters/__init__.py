from __future__ import annotations

# Публичный API пакета adapters:
#  • process_groups — движок обработки (старый)
#  • process_files — движок обработки файлов (V2) 
#  • get_adapter_for_path — ленивое получение класса адаптера по пути
from .engine import process_groups
from .processor_v2 import process_files
from .registry import get_adapter_for_path, register_lazy

__all__ = ["process_groups", "process_files", "get_adapter_for_path", "register_lazy"]

# ---- Лёгкая (ленивая) регистрация встроенных адаптеров --------------------
# Никаких импортов тяжёлых модулей здесь нет — только строки module:class.
# Модуль адаптера будет импортирован ровно в момент первого запроса по расширению.

# Tree-sitter based adapters
register_lazy(module=".python", class_name="PythonAdapter", extensions=[".py"])
register_lazy(module=".typescript", class_name="TypeScriptAdapter", extensions=[".ts", ".tsx"])

# Markdown adapter
register_lazy(module=".markdown", class_name="MarkdownAdapter", extensions=[".md", ".markdown"])

# Stub adapters for future languages (M7 implementation)
# register_lazy(module=".javascript", class_name="JavaScriptAdapter", extensions=[".js", ".jsx"])
# register_lazy(module=".java", class_name="JavaAdapter", extensions=[".java"])
# register_lazy(module=".cpp", class_name="CppAdapter", extensions=[".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"])
# register_lazy(module=".scala", class_name="ScalaAdapter", extensions=[".scala"])

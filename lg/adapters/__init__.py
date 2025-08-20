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
register_lazy(module=".python", class_name="PythonAdapter", extensions=[".py"])
register_lazy(module=".markdown", class_name="MarkdownAdapter", extensions=[".md", ".markdown"])

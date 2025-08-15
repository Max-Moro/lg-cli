from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> str:
    """
    Минимальный JSON-дампер для простых ответов CLI.
    — без prettify; ensure_ascii=False; без заботы о завершающем \n (CLI решает сам).
    """
    return json.dumps(obj, ensure_ascii=False)

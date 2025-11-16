from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> str:
    """
    Minimal JSON dumper for simple CLI responses.
    — no prettify; ensure_ascii=False; no care for trailing \n (CLI decides).
    """
    return json.dumps(obj, ensure_ascii=False)

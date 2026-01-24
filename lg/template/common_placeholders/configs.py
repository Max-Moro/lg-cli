"""
Resource configurations for common placeholders.

Defines configs for templates and contexts.
Section config moved to lg/addressing/configs.py to avoid circular imports.
"""

from __future__ import annotations

from ...addressing import ResourceConfig

# Template reference: .tpl.md extension, resolved inside lg-cfg/
TEMPLATE_CONFIG = ResourceConfig(
    kind="tpl",
    extension=".tpl.md",
)

# Context reference: .ctx.md extension, resolved inside lg-cfg/
CONTEXT_CONFIG = ResourceConfig(
    kind="ctx",
    extension=".ctx.md",
)


__all__ = ["TEMPLATE_CONFIG", "CONTEXT_CONFIG"]

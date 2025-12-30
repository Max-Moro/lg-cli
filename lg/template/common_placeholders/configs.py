"""
Resource configurations for common placeholders.

Defines configs for sections, templates, and contexts.
"""

from __future__ import annotations

from ..addressing import ResourceConfig

# Section reference: no file extension, resolved inside lg-cfg/
SECTION_CONFIG = ResourceConfig(
    name="section",
    extension=None,
)

# Template reference: .tpl.md extension, resolved inside lg-cfg/
TEMPLATE_CONFIG = ResourceConfig(
    name="template",
    extension=".tpl.md",
)

# Context reference: .ctx.md extension, resolved inside lg-cfg/
CONTEXT_CONFIG = ResourceConfig(
    name="context",
    extension=".ctx.md",
)


__all__ = ["SECTION_CONFIG", "TEMPLATE_CONFIG", "CONTEXT_CONFIG"]

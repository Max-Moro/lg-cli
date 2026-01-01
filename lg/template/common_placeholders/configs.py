"""
Resource configurations for common placeholders.

Defines configs for sections, templates, and contexts.
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

# Section reference: resolved via SectionService
SECTION_CONFIG = ResourceConfig(
    kind="sec",
    is_section=True,
)


__all__ = ["TEMPLATE_CONFIG", "CONTEXT_CONFIG", "SECTION_CONFIG"]

"""
Resource configurations for markdown placeholders.

Defines configs for markdown files inside and outside lg-cfg/.
"""

from __future__ import annotations

from ...addressing import ResourceConfig

# Markdown inside lg-cfg/ (with @origin:path): strip MD syntax, resolved inside lg-cfg/
MARKDOWN_CONFIG = ResourceConfig(
    name="markdown",
    extension=".md",
    strip_md_syntax=True,
)

# Markdown outside lg-cfg/ (relative to scope root): strip MD syntax, resolved in scope dir
MARKDOWN_EXTERNAL_CONFIG = ResourceConfig(
    name="markdown_external",
    extension=".md",
    strip_md_syntax=True,
    resolve_outside_cfg=True,
)


__all__ = ["MARKDOWN_CONFIG", "MARKDOWN_EXTERNAL_CONFIG"]

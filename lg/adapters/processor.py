"""
File processor.

Processing files through language adapters.
"""

from __future__ import annotations

from typing import Dict, List, cast

from ..adapters.base import BaseAdapter
from ..adapters.context import LightweightContext
from ..adapters.registry import get_adapter_for_path
from ..filtering.fs import read_text
from ..template.context import TemplateContext
from ..types import ProcessedFile, SectionPlan


def process_files(plan: SectionPlan, template_ctx: TemplateContext) -> List[ProcessedFile]:
    """
    Process files through language adapters.

    Args:
        plan: Section plan with files to process
        template_ctx: Template context with settings and services

    Returns:
        List of processed files
    """
    processed_files = []
    cache = template_ctx.run_ctx.cache

    # Cache bound adapters for efficiency
    bound_cache: Dict[tuple[str, tuple[tuple[str, object], ...]], BaseAdapter] = {}

    # Total section size for context (number of files)
    total_files = len(plan.files)

    for file_entry in plan.files:
        fp = file_entry.abs_path
        adapter_cls = get_adapter_for_path(fp)

        # Get adapter configuration (section + overrides)
        sec_raw_cfg = plan.manifest.adapters_cfg.get(adapter_cls.name)
        override_cfg = file_entry.adapter_overrides.get(adapter_cls.name)

        raw_cfg = None
        if sec_raw_cfg or override_cfg:
            raw_cfg = dict(sec_raw_cfg or {})
            raw_cfg.update(dict(override_cfg or {}))

        # Create or get bound adapter
        cfg_key = _freeze_cfg(raw_cfg or {})
        bkey = (adapter_cls.name, cfg_key)
        adapter = bound_cache.get(bkey)
        if adapter is None:
            adapter = adapter_cls.bind(raw_cfg, template_ctx.run_ctx.tokenizer)
            bound_cache[bkey] = adapter

        # Type casting for correct typing
        adapter = cast(BaseAdapter, adapter)

        # Read file content
        raw_text = read_text(fp)

        # Get file label from plan
        file_label = plan.labels[file_entry.rel_path]

        # Create context for adapter
        lightweight_ctx = LightweightContext(
            file_path=fp,
            raw_text=raw_text,
            group_size=total_files,
            template_ctx=template_ctx,
            file_label=file_label
        )

        # Check skip heuristics
        if adapter.name != "base" and adapter.should_skip(lightweight_ctx):
            continue

        # Build cache keys
        k_proc, p_proc = cache.build_processed_key(
            abs_path=fp,
            adapter_cfg=raw_cfg,
            active_tags=template_ctx.current_state.active_tags,
        )

        # Try to get from cache
        cached = cache.get_processed(p_proc)
        if cached and "processed_text" in cached:
            processed_text = cached["processed_text"]
            meta = cached.get("meta", {}) or {}
        else:
            # Process file with adapter
            processed_text, meta = adapter.process(lightweight_ctx)

            # Cache result
            cache.put_processed(p_proc, processed_text=processed_text, meta=meta)

        # Create ProcessedFile
        processed_file = ProcessedFile(
            abs_path=fp,
            rel_path=file_entry.rel_path,
            processed_text=processed_text.rstrip("\n") + "\n",
            meta=meta,
            raw_text=raw_text,
            cache_key=k_proc
        )

        processed_files.append(processed_file)

    # Sort for stable order
    processed_files.sort(key=lambda f: f.rel_path)
    return processed_files


def _freeze_cfg(obj) -> tuple:
    """
    Make object hashable and deterministic for adapter caching.
    """
    if isinstance(obj, dict):
        return tuple((k, _freeze_cfg(v)) for k, v in sorted(obj.items(), key=lambda kv: kv[0]))
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze_cfg(x) for x in obj)
    if isinstance(obj, set):
        return tuple(sorted(_freeze_cfg(x) for x in obj))
    return obj


__all__ = ["process_files"]
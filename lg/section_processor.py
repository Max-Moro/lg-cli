"""
Section processor.

Implements processing of individual sections requested by template engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .adapters.processor import process_files
from .config import Config, load_config
from .filtering.manifest import build_section_manifest
from .rendering import render_section, build_section_plan
from .run_context import RunContext
from .stats.collector import StatsCollector
from .template.context import TemplateContext
from .types import RenderedSection, SectionRef, SectionManifest


class SectionProcessor:
    """
    Processes a single section on request.
    """

    def __init__(self, run_ctx: RunContext, stats_collector: StatsCollector):
        """
        Initialize section processor.

        Args:
            run_ctx: Execution context with settings and services
            stats_collector: Statistics collector for delegating all calculations
        """
        self.run_ctx = run_ctx
        self.stats_collector = stats_collector
        # Cache configurations for each scope_dir
        self._config_cache: Dict[Path, Config] = {}

    def _get_config(self, scope_dir: Path) -> Config:
        """
        Get configuration for specified scope_dir with caching.

        Args:
            scope_dir: Directory with configuration

        Returns:
            Loaded configuration
        """
        if scope_dir not in self._config_cache:
            self._config_cache[scope_dir] = load_config(scope_dir)
        return self._config_cache[scope_dir]

    def _build_manifest(self, section_ref: SectionRef, template_ctx: TemplateContext) -> SectionManifest:
        """
        Build section manifest using cached configuration.

        Args:
            section_ref: Section reference
            template_ctx: Template context

        Returns:
            Section manifest
        """
        # Check if there's a virtual section in the context
        virtual_section_config = template_ctx.get_virtual_section()

        if virtual_section_config is not None:
            # Use virtual section
            section_config = virtual_section_config
        else:
            # Get configuration with caching
            config = self._get_config(section_ref.scope_dir)
            section_config = config.sections.get(section_ref.name)

            if not section_config:
                available = list(config.sections.keys())
                raise RuntimeError(
                    f"Section '{section_ref.name}' not found in {section_ref.scope_dir}. "
                    f"Available: {', '.join(available) if available else '(none)'}"
                )

        manifest = build_section_manifest(
            section_ref=section_ref,
            section_config=section_config,
            template_ctx=template_ctx,
            root=self.run_ctx.root,
            vcs=self.run_ctx.vcs,
            vcs_mode=template_ctx.current_state.mode_options.vcs_mode,
            target_branch=self.run_ctx.options.target_branch
        )

        # For virtual sections (md-placeholders), check file existence
        if virtual_section_config is not None and not manifest.files:
            # This is our virtual section for md-placeholder
            # Try to recover placeholder information from filters
            if manifest.ref.scope_rel:
                # Addressable placeholder
                raise RuntimeError(f"No markdown files found for `md@{manifest.ref.scope_rel}:` placeholder")
            else:
                # Regular placeholder, try to get path from section configuration
                virtual_cfg = template_ctx.get_virtual_section()
                if virtual_cfg and virtual_cfg.filters.allow:
                    file_path = virtual_cfg.filters.allow[0].lstrip('/')
                    if file_path.startswith('lg-cfg/'):
                        raise RuntimeError(f"No markdown files found for `md@self:{file_path[7:]}` placeholder")
                    else:
                        raise RuntimeError(f"No markdown files found for `md:{file_path}` placeholder")
                else:
                    raise RuntimeError("No markdown files found for `md:` placeholder")

        return manifest

    def process_section(self, section_ref: SectionRef, template_ctx: TemplateContext) -> RenderedSection:
        """
        Process a single section and return its rendered content.

        Args:
            section_ref: Section reference
            template_ctx: Current template context (contains active modes, tags)

        Returns:
            Rendered section
        """
        manifest = self._build_manifest(section_ref, template_ctx)

        plan = build_section_plan(manifest, template_ctx)

        processed_files = process_files(plan, template_ctx)

        # Register processed files in statistics collector
        for pf in processed_files:
            self.stats_collector.register_processed_file(
                file=pf,
                section_ref=section_ref
            )

        rendered = render_section(plan, processed_files)

        # Register rendered section in statistics collector
        self.stats_collector.register_section_rendered(rendered)

        return rendered

__all__ = ["SectionProcessor"]
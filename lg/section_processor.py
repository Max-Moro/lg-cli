"""
Section processor.

Implements processing of individual sections requested by template engine.
"""

from __future__ import annotations

from .adapters.processor import process_files
from .filtering.manifest import build_section_manifest
from .rendering import render_section, build_section_plan
from .run_context import RunContext
from .stats.collector import StatsCollector
from .template.context import TemplateContext
from .addressing.types import ResolvedSection
from .types import RenderedSection, SectionManifest


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

    def _build_manifest(self, resolved: ResolvedSection, template_ctx: TemplateContext) -> SectionManifest:
        """
        Build section manifest using resolved section.

        Args:
            resolved: Resolved section with loaded configuration
            template_ctx: Template context

        Returns:
            Section manifest
        """
        # Simply use section_config from resolved - no virtual section check needed
        manifest = build_section_manifest(
            resolved=resolved,
            section_config=resolved.section_config,
            template_ctx=template_ctx,
            root=self.run_ctx.root,
            vcs=self.run_ctx.vcs,
            gitignore_service=self.run_ctx.gitignore,
            vcs_mode=template_ctx.current_state.mode_options.vcs_mode,
            target_branch=self.run_ctx.options.target_branch
        )

        # For virtual sections (md-placeholders), check file existence
        if not manifest.files and not manifest.is_local_files:
            # Check if this looks like a virtual md section
            if resolved.name.startswith("md:") or resolved.name.startswith("md@"):
                raise RuntimeError(f"No markdown files found for `{resolved.name}` placeholder")

        return manifest

    def process_section(self, resolved: ResolvedSection, template_ctx: TemplateContext) -> RenderedSection:
        """
        Process a resolved section and return its rendered content.

        Args:
            resolved: Fully resolved section (from resolver)
            template_ctx: Current template context (contains active modes, tags)

        Returns:
            Rendered section
        """
        manifest = self._build_manifest(resolved, template_ctx)

        plan = build_section_plan(manifest, template_ctx)

        processed_files = process_files(plan, template_ctx)

        # Register processed files in statistics collector
        for pf in processed_files:
            self.stats_collector.register_processed_file(
                file=pf,
                resolved=resolved
            )

        rendered = render_section(plan, processed_files)

        # Register rendered section in statistics collector
        self.stats_collector.register_section_rendered(rendered)

        return rendered

__all__ = ["SectionProcessor"]
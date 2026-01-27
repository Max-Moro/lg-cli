"""
Main processing pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, cast

from .cache.fs_cache import Cache
from .paths import cfg_root
from .migrate import ensure_cfg_actual
from .run_context import RunContext
from .section_processor import SectionProcessor
from .section import SectionService
from .stats import RunResult, build_run_result_from_collector, StatsCollector
from .stats.tokenizer import TokenService
from .template import create_template_processor, TemplateContext
from .addressing import AddressingContext, SECTION_CONFIG
from .addressing.types import ResolvedSection
from .types import RunOptions, TargetSpec
from .git import NullVcs, GitVcs, is_git_repo
from .git import GitIgnoreService
from .version import tool_version
from .adaptive.context_resolver import ContextResolver
from .adaptive.model import AdaptiveModel


class Engine:
    """
    Engine coordinating class.

    Manages interaction between components:
    - TemplateProcessor for template processing (created per-render)
    - SectionProcessor for section processing
    - StatsCollector for statistics collection
    """

    def __init__(self, options: RunOptions):
        """
        Initialize engine with specified options.

        Args:
            options: Execution options
        """
        self.options = options
        self.root = Path.cwd().resolve()

        # --- Infrastructure ---
        tool_ver = tool_version()
        cache = Cache(self.root, enabled=None, fresh=False, tool_version=tool_ver)
        has_git = is_git_repo(self.root)
        vcs = GitVcs() if has_git else NullVcs()
        gitignore = GitIgnoreService(self.root) if has_git else None
        tokenizer = TokenService(
            root=self.root,
            lib=self.options.tokenizer_lib,
            encoder=self.options.encoder,
            cache=cache
        )

        # --- Services ---
        section_service = SectionService(self.root, cache)
        addressing = AddressingContext(
            repo_root=self.root,
            initial_cfg_root=self.root / "lg-cfg",
            section_service=section_service
        )

        self.run_ctx = RunContext(
            root=self.root,
            options=self.options,
            cache=cache,
            vcs=vcs,
            gitignore=gitignore,
            tokenizer=tokenizer,
            addressing=addressing,
        )

        # --- Processing components ---
        self.stats_collector = StatsCollector(
            self.run_ctx.options.ctx_limit,
            self.run_ctx.tokenizer
        )

        self.context_resolver = ContextResolver(
            section_service=section_service,
            addressing=self.run_ctx.addressing,
            cfg_root=self.run_ctx.root / "lg-cfg",
        )

        self.section_processor = SectionProcessor(
            run_ctx=self.run_ctx,
            stats_collector=self.stats_collector
        )

    def render_context(self, context_name: str) -> str:
        """
        Render context from template.

        Args:
            context_name: Context name to render

        Returns:
            Rendered document

        Raises:
            TemplateProcessingError: On template processing error
            FileNotFoundError: If context template not found
        """
        # Ensure configuration is up to date
        ensure_cfg_actual(cfg_root(self.root))

        # Set target in statistics collector
        self.stats_collector.set_target_name(f"ctx:{context_name}")

        # Resolve adaptive model for this context
        adaptive_data = self.context_resolver.resolve_for_context(context_name)

        # Create template processor with resolved model
        template_processor = self._create_template_processor(adaptive_data.model)

        # Process template
        final_text = template_processor.process_template_file(context_name)

        # Set final texts in collector
        self.stats_collector.set_final_texts(final_text)

        return final_text

    def render_section(self, section_name: str) -> str:
        """
        Render individual section.

        Args:
            section_name: Section name to render (may be an addressable reference)

        Returns:
            Rendered document
        """
        # Ensure configuration is up to date
        ensure_cfg_actual(cfg_root(self.root))

        # Set target in statistics collector
        self.stats_collector.set_target_name(f"sec:{section_name}")

        # Resolve adaptive model for this section
        adaptive_model = self.context_resolver.resolve_for_section(
            section_name,
            scope_dir=self.run_ctx.root,
        )

        template_ctx = TemplateContext(self.run_ctx, adaptive_model)

        # Resolve section reference
        resolved_section = cast(ResolvedSection, self.run_ctx.addressing.resolve(section_name, SECTION_CONFIG))
        rendered_section = self.section_processor.process_section(resolved_section, template_ctx)

        # Set final texts in collector
        self.stats_collector.set_final_texts(rendered_section.text)

        return rendered_section.text

    def render_text(self, target_spec: TargetSpec) -> str:
        """
        Render final text.

        Args:
            target_spec: Target specification for report

        Returns:
            Rendered context or section
        """
        if target_spec.kind == "context":
            return self.render_context(target_spec.name)
        else:
            return self.render_section(target_spec.name)

    def generate_report(self, target_spec: TargetSpec) -> RunResult:
        """
        Generate complete report with statistics.

        Args:
            target_spec: Target specification for report

        Returns:
            RunResult model in API v4 format
        """
        if target_spec.kind == "context":
            self.render_context(target_spec.name)
        else:
            self.render_section(target_spec.name)

        return build_run_result_from_collector(
            collector=self.stats_collector,
            target_spec=target_spec,
        )

    def _create_template_processor(self, adaptive_model: AdaptiveModel):
        """
        Create template processor initialized with adaptive model.

        Creates TemplateProcessor with plugins and wires the section handler.
        Called per-render when the adaptive model is available.

        Args:
            adaptive_model: Resolved AdaptiveModel for the target

        Returns:
            Fully configured TemplateProcessor
        """
        template_processor = create_template_processor(self.run_ctx, adaptive_model)

        def section_handler(resolved: ResolvedSection, template_ctx: TemplateContext) -> str:
            rendered_section = self.section_processor.process_section(resolved, template_ctx)
            return rendered_section.text

        template_processor.set_section_handler(section_handler)
        return template_processor


# ----------------------------- Entry Points ----------------------------- #

def _parse_target(target: str, root: Optional[Path] = None) -> TargetSpec:
    """
    Parse target string into TargetSpec.

    Args:
        target: Target string in format "ctx:name", "sec:name" or "name"
        root: Project root (if None, cwd is used)

    Returns:
        Target specification
    """
    from .template.common import CTX_SUFFIX

    if root is None:
        root = Path.cwd().resolve()
    else:
        root = root.resolve()
    cfg_path = cfg_root(root)

    kind = "auto"
    name = target.strip()

    if name.startswith("ctx:"):
        kind, name = "context", name[4:]
    elif name.startswith("sec:"):
        kind, name = "section", name[4:]

    # For auto mode, check if context exists
    if kind in ("auto", "context"):
        template_path = cfg_path / f"{name}{CTX_SUFFIX}"
        if template_path.is_file():
            return TargetSpec(
                kind="context",
                name=name,
                template_path=template_path
            )
        if kind == "context":
            raise FileNotFoundError(f"Context template not found: {template_path}")

    # Fallback to section
    return TargetSpec(
        kind="section",
        name=name,
        template_path=Path()  # Not used for sections
    )


def run_render(target: str, options: RunOptions) -> str:
    """Entry point for rendering."""
    engine = Engine(options)
    target_spec = _parse_target(target, engine.root)
    return engine.render_text(target_spec)


def run_report(target: str, options: RunOptions) -> RunResult:
    """Entry point for report generation."""
    engine = Engine(options)
    target_spec = _parse_target(target, engine.root)
    return engine.generate_report(target_spec)


__all__ = [
    "Engine",
    "run_render",
    "run_report",
]
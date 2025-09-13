from __future__ import annotations

"""
BudgetController: token-per-file budgeting with priority-based escalation.

Works in a sandbox (placeholders disabled) to pick an effective CodeCfg
that will later be used for the real optimization pipeline.
"""

from dataclasses import replace
from typing import Dict, List, Optional, Tuple, cast, Generic, TypeVar
import copy

from .code_model import (
    CodeCfg,
    BudgetConfig,
    ImportConfig,
    CommentConfig,
    LiteralConfig,
    FunctionBodyConfig,
    ImportPolicy,
    CommentPolicy,
    FunctionBodyStrip,
)
from .context import ProcessingContext
from .range_edits import RangeEditor
from .optimizations import (
    ImportOptimizer,
    CommentOptimizer,
    LiteralOptimizer,
    FunctionBodyOptimizer,
    PublicApiOptimizer,
)


Cc = TypeVar("Cc", bound=CodeCfg)


class BudgetController(Generic[Cc]):
    """
    Controller that simulates optimizations in a sandbox to select an
    effective configuration that respects a per-file token budget.

    In sandbox mode, placeholders are disabled (style = "none") to avoid
    adding any extra tokens while we measure savings. The controller never
    mutates the real ProcessingContext or calls CodeAdapter._apply_optimizations.
    It only returns an adjusted CodeCfg and budget metrics.
    """

    def __init__(self, adapter, tokenizer, cfg_budget: BudgetConfig):
        self.adapter = adapter
        self.tokenizer = tokenizer
        self.cfg_budget = cfg_budget

        # Default escalation order when not overridden by user
        self.order: List[str] = self.cfg_budget.priority_order or [
            "imports_external",
            "literals",
            "comments",
            "imports_local",
            "private_bodies",
            "public_api_only",
            "public_bodies",
            "docstrings_first_sentence",
        ]

    # --------------------- public API --------------------- #
    def fit_config(self, lightweight_ctx, base_cfg: Cc) -> Tuple[Cc, Dict[str, int]]:
        """
        Pick an effective configuration to satisfy budget.

        Args:
            lightweight_ctx: LightweightContext with raw_text/filename/ext
            base_cfg: CodeCfg from adapter (user configuration)

        Returns:
            (effective_cfg, metrics)
        """
        limit = self.cfg_budget.max_tokens_per_file
        metrics: Dict[str, int] = {}
        lang_prefix = self.adapter.name

        if not limit or limit <= 0:
            # Budget disabled
            return base_cfg, metrics

        raw_text = lightweight_ctx.raw_text or ""
        tokens_before = self.tokenizer.count_text(raw_text)
        metrics[f"{lang_prefix}.budget.tokens_before"] = tokens_before

        if tokens_before <= limit:
            metrics[f"{lang_prefix}.budget.tokens_after"] = tokens_before
            return base_cfg, metrics

        # Clone cfg so we can evolve it step-by-step
        effective_cfg: Cc = copy.deepcopy(base_cfg)

        # Start from user's policies applied in sandbox
        text_current = raw_text
        text_current = self._apply_user_policies(lightweight_ctx, text_current, base_cfg)

        tokens_after_user = self.tokenizer.count_text(text_current)
        if tokens_after_user <= limit:
            metrics[f"{lang_prefix}.budget.tokens_after"] = tokens_after_user
            # No need to escalate, return user's cfg as effective
            return effective_cfg, metrics

        # Build escalation order (skip steps already covered by user's cfg where applicable)
        order = self._resolve_priority_order(base_cfg)

        # Baselines for multi-level steps so they re-calc from the same start
        literals_baseline: Optional[str] = None
        comments_baseline: Optional[str] = None

        # Track cumulative savings per step
        last_tokens = tokens_after_user

        for step in order:
            step_after_text = ""

            if step == "imports_external":
                step_after_text = self._apply_imports(lightweight_ctx, text_current, policy="strip_external", summarize_long=True)
                effective_cfg.imports = replace(effective_cfg.imports, policy="strip_external", summarize_long=True)

            elif step == "literals":
                if literals_baseline is None:
                    literals_baseline = text_current
                # Walk levels: start from user's setting (if any) then go down powers of two
                levels = self._compute_levels_for_limit(base_cfg.literals.max_tokens)
                candidate_text = None
                chosen_level = base_cfg.literals.max_tokens
                for lvl in levels:
                    candidate_text = self._apply_literals(lightweight_ctx, literals_baseline, max_tokens=lvl)
                    chosen_level = lvl
                    if self.tokenizer.count_text(candidate_text) <= limit:
                        break
                # Commit candidate only after levels exploration
                if candidate_text is not None:
                    step_after_text = candidate_text
                    # Update effective cfg with chosen literal limit
                    effective_cfg.literals = replace(effective_cfg.literals, max_tokens=chosen_level)

            elif step == "comments":
                if comments_baseline is None:
                    comments_baseline = text_current
                levels = self._compute_levels_for_limit(self._extract_comment_max_tokens(base_cfg))
                candidate_text = None
                chosen_level = self._extract_comment_max_tokens(base_cfg)
                for lvl in levels:
                    candidate_text = self._apply_comments(lightweight_ctx, comments_baseline, policy="keep_doc", max_tokens=lvl)
                    chosen_level = lvl
                    if self.tokenizer.count_text(candidate_text) <= limit:
                        break
                if candidate_text is not None:
                    step_after_text = candidate_text
                    # Update effective cfg comments
                    # Ensure we keep docs but may add max_tokens limit
                    effective_cfg.comment_policy = CommentConfig(policy=cast(CommentPolicy, "keep_doc"), max_tokens=chosen_level)

            elif step == "imports_local":
                step_after_text = self._apply_imports(lightweight_ctx, text_current, policy="strip_local", summarize_long=True)
                # Do not override if already strip_all
                new_policy = effective_cfg.imports.policy
                if new_policy != "strip_all":
                    new_policy = cast(ImportPolicy, "strip_local")
                effective_cfg.imports = replace(effective_cfg.imports, policy=new_policy, summarize_long=True)

            elif step == "private_bodies":
                step_after_text = self._apply_function_bodies(lightweight_ctx, text_current, mode="non_public")
                # Strengthen function body config
                eff_sfb = effective_cfg.strip_function_bodies
                if isinstance(eff_sfb, bool) and eff_sfb is True:
                    # Upgrade to a structured config prioritizing non_public
                    effective_cfg.strip_function_bodies = FunctionBodyConfig(mode=cast(FunctionBodyStrip, "non_public"))
                elif isinstance(eff_sfb, FunctionBodyConfig):
                    effective_cfg.strip_function_bodies = replace(eff_sfb, mode=cast(FunctionBodyStrip, "non_public"))
                else:
                    effective_cfg.strip_function_bodies = FunctionBodyConfig(mode=cast(FunctionBodyStrip, "non_public"))

            elif step == "public_api_only":
                step_after_text = self._apply_public_api_only(lightweight_ctx, text_current)
                effective_cfg.public_api_only = True

            elif step == "public_bodies":
                # "non_public" + "public_only" вместе дают "all", поэтому тут "all", а не "public_only"
                step_after_text = self._apply_function_bodies(lightweight_ctx, text_current, mode="all")
                eff_sfb = effective_cfg.strip_function_bodies
                if isinstance(eff_sfb, bool) and eff_sfb is True:
                    effective_cfg.strip_function_bodies = FunctionBodyConfig(mode=cast(FunctionBodyStrip, "all"))
                elif isinstance(eff_sfb, FunctionBodyConfig):
                    effective_cfg.strip_function_bodies = replace(eff_sfb, mode=cast(FunctionBodyStrip, "all"))
                else:
                    effective_cfg.strip_function_bodies = FunctionBodyConfig(mode=cast(FunctionBodyStrip, "all"))

            elif step == "docstrings_first_sentence":
                step_after_text = self._apply_comments(lightweight_ctx, text_current, policy="keep_first_sentence", max_tokens=None)
                effective_cfg.comment_policy = cast(CommentPolicy, "keep_first_sentence")

            # Commit step
            text_current = step_after_text

            # Save step metrics
            cur_tokens = self.tokenizer.count_text(text_current)
            saved = max(0, last_tokens - cur_tokens)
            metrics[f"{lang_prefix}.budget.steps.{step}"] = saved
            last_tokens = cur_tokens

            if cur_tokens <= limit:
                break

        metrics[f"{lang_prefix}.budget.tokens_after"] = last_tokens
        return effective_cfg, metrics

    # --------------------- helpers --------------------- #
    def _resolve_priority_order(self, base_cfg: CodeCfg) -> List[str]:
        # Skip steps that are already as-strong-as user settings
        def already_covers(step: str) -> bool:
            if step == "imports_external":
                return base_cfg.imports.policy in (cast(ImportPolicy, "strip_external"), cast(ImportPolicy, "strip_all"))
            if step == "imports_local":
                return base_cfg.imports.policy in (cast(ImportPolicy, "strip_local"), cast(ImportPolicy, "strip_all"))
            if step == "public_api_only":
                return bool(base_cfg.public_api_only)
            if step == "public_bodies":
                sfb = base_cfg.strip_function_bodies
                if isinstance(sfb, bool):
                    return bool(sfb)
                return getattr(sfb, "mode", "none") in ("public_only", "all")
            if step == "private_bodies":
                sfb = base_cfg.strip_function_bodies
                if isinstance(sfb, bool):
                    return bool(sfb)
                return getattr(sfb, "mode", "none") in ("non_public", "all")
            # For literals/comments we always keep steps, as we may tighten limits
            return False

        return [s for s in self.order if not already_covers(s)]

    def _make_sandbox_context(self, lightweight_ctx, text: str) -> ProcessingContext:
        # Build ProcessingContext manually to force placeholder style "none"
        doc = self.adapter.create_document(text, lightweight_ctx.ext)
        editor = RangeEditor(text)
        # Construct a placeholder manager directly with style "none"
        from .placeholders import create_placeholder_manager
        placeholders = create_placeholder_manager(text, self.adapter.get_comment_style(), "none")

        return ProcessingContext(
            file_path=lightweight_ctx.file_path,
            raw_text=text,
            group_size=lightweight_ctx.group_size,
            mixed=lightweight_ctx.mixed,
            adapter_name=self.adapter.name,
            doc=doc,
            editor=editor,
            placeholders=placeholders,
            tokenizer=self.tokenizer,
        )

    def _apply_user_policies(self, lightweight_ctx, text: str, cfg: CodeCfg) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)

        # Respect user's base settings as the starting point
        if cfg.public_api_only:
            PublicApiOptimizer(self.adapter).apply(ctx)

        if cfg.strip_function_bodies:
            FunctionBodyOptimizer(cfg.strip_function_bodies, self.adapter).apply(ctx)

        # Comments
        if cfg.comment_policy != "keep_all":
            CommentOptimizer(cfg.comment_policy, self.adapter).apply(ctx)

        # Imports and literals always safe to run (no-op if default)
        ImportOptimizer(cfg.imports, self.adapter).apply(ctx)
        LiteralOptimizer(cfg.literals, self.adapter).apply(ctx)

        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _apply_imports(self, lightweight_ctx, text: str, *, policy: str, summarize_long: bool) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)
        cfg = ImportConfig(policy=cast(ImportPolicy, policy), summarize_long=summarize_long)
        ImportOptimizer(cfg, self.adapter).apply(ctx)
        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _apply_literals(self, lightweight_ctx, text: str, *, max_tokens: Optional[int]) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)
        cfg = LiteralConfig(max_tokens=max_tokens)
        LiteralOptimizer(cfg, self.adapter).apply(ctx)
        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _apply_comments(self, lightweight_ctx, text: str, *, policy: str, max_tokens: Optional[int]) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)
        cfg = CommentConfig(policy=cast(CommentPolicy, policy), max_tokens=max_tokens)
        CommentOptimizer(cfg, self.adapter).apply(ctx)
        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _apply_function_bodies(self, lightweight_ctx, text: str, *, mode: str) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)
        cfg = FunctionBodyConfig(mode=cast(FunctionBodyStrip, mode))
        FunctionBodyOptimizer(cfg, self.adapter).apply(ctx)
        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _apply_public_api_only(self, lightweight_ctx, text: str) -> str:
        ctx = self._make_sandbox_context(lightweight_ctx, text)
        PublicApiOptimizer(self.adapter).apply(ctx)
        new_text, _ = ctx.editor.apply_edits()
        return new_text

    def _compute_levels_for_limit(self, user_level: Optional[int]) -> List[int]:
        # Start from user's level if provided, then go down powers of two to 32
        ladder = [512, 256, 128, 64, 32]
        if user_level is None:
            return ladder
        # Include user's level and then smaller levels from ladder
        levels: List[int] = [user_level]
        for lv in ladder:
            if lv < user_level:
                levels.append(lv)
        # Ensure unique and descending-ish order preserving sequence
        seen = set()
        uniq = []
        for lv in levels:
            if lv not in seen:
                uniq.append(lv)
                seen.add(lv)
        return uniq or ladder

    @staticmethod
    def _extract_comment_max_tokens(cfg: CodeCfg) -> Optional[int]:
        cp = cfg.comment_policy
        if isinstance(cp, str):
            return None
        try:
            return cast(CommentConfig, cp).max_tokens
        except Exception:
            return None

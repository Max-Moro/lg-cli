from __future__ import annotations

"""
Budget System controller (M7).

Applies stepwise, escalating optimizations until a per-file token budget is met.
Works on the ProcessingContext by temporarily disabling placeholders (style="none"),
committing edits between steps (commit-and-reseed), and recording basic telemetry.
"""

from dataclasses import replace
from typing import List, Optional

from .code_model import (
    CodeCfg,
    CommentConfig,
    ImportConfig,
    LiteralConfig,
    FunctionBodyConfig,
)
from .context import ProcessingContext
from .optimizations import (
    ImportOptimizer,
    CommentOptimizer,
    LiteralOptimizer,
    FunctionBodyOptimizer,
    PublicApiOptimizer,
)
from .range_edits import RangeEditor


DEFAULT_ORDER: List[str] = [
    "imports_external",
    "literals",
    "comments",
    "imports_local",
    "private_bodies",
    "public_api_only",
    "public_bodies",
    "docstrings_first_sentence",
]


class BudgetController:
    def __init__(self, *, adapter, tokenizer, cfg: CodeCfg):
        self.adapter = adapter
        self.tok = tokenizer
        self.cfg = cfg

    def run(self, context: ProcessingContext) -> None:
        budget = getattr(self.cfg, "budget", None)
        limit = getattr(budget, "max_tokens_per_file", None)
        if not limit:
            return

        # Record initial tokens
        tokens_before = self.tok.count_text(context.raw_text or "")
        context.metrics.set(f"{self.adapter.name}.budget.tokens_before", tokens_before)
        if tokens_before <= int(limit):
            return

        original_placeholder_style = context.placeholders.placeholder_style
        # Disable placeholders during budget steps (pure deletions where applicable)
        context.placeholders.placeholder_style = "none"

        order = self._resolve_order()
        tokens_prev = tokens_before

        for step in order:
            self._apply_step(step, context, limit)

            # Commit and reseed after each step
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")

            tokens_now = self.tok.count_text(context.raw_text or "")
            context.metrics.set(f"{self.adapter.name}.budget.steps.{step}", max(0, tokens_prev - tokens_now))
            tokens_prev = tokens_now

            if tokens_now <= int(limit):
                break

        # Final tokens
        tokens_after = self.tok.count_text(context.raw_text or "")
        context.metrics.set(f"{self.adapter.name}.budget.tokens_after", tokens_after)

        # Restore placeholder style for subsequent normal optimization and finalization
        context.placeholders.placeholder_style = original_placeholder_style

    # ---------------- internals ---------------- #
    def _resolve_order(self) -> List[str]:
        budget = getattr(self.cfg, "budget", None)
        order = list(getattr(budget, "priority_order", []) or [])
        # Sanitize/custom fallback
        if not order:
            order = list(DEFAULT_ORDER)
        return [s for s in order if s in set(DEFAULT_ORDER)]

    def _apply_step(self, step: str, context: ProcessingContext, limit: int) -> None:
        if step == "imports_external":
            self._apply_imports(context, policy="strip_external")
        elif step == "imports_local":
            self._apply_imports(context, policy="strip_local")
        elif step == "literals":
            self._apply_literals_levels(context, limit)
        elif step == "comments":
            self._apply_comments_levels(context, limit)
        elif step == "private_bodies":
            self._apply_function_bodies(context, mode="non_public")
        elif step == "public_api_only":
            PublicApiOptimizer(self.adapter).apply(context)
        elif step == "public_bodies":
            self._apply_function_bodies(context, mode="public_only")
        elif step == "docstrings_first_sentence":
            # Keep first sentence of documentation; non-doc comments may be removed
            CommentOptimizer("keep_first_sentence", self.adapter).apply(context)

    def _apply_imports(self, context: ProcessingContext, *, policy: str) -> None:
        # typing: ImportPolicy literal
        cfg = ImportConfig(policy=policy, summarize_long=True)  # type: ignore[arg-type]
        ImportOptimizer(cfg, self.adapter).apply(context)

    def _apply_literals_levels(self, context: ProcessingContext, limit: int) -> None:
        # Conservative descending levels
        levels = [512, 256, 128, 64, 32]
        # If file is huge vs limit, start from min(limit//2, 512) roughly
        tokens_now = self.tok.count_text(context.raw_text or "")
        start_idx = 0
        if tokens_now > 0 and limit:
            # rough heuristic to skip too-loose levels
            for i, lvl in enumerate(levels):
                if lvl <= max(32, int(limit) // 2):
                    start_idx = i
                    break
        for lvl in levels[start_idx:]:
            LiteralOptimizer(LiteralConfig(max_tokens=lvl), self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")
            if self.tok.count_text(context.raw_text or "") <= int(limit):
                break

    def _apply_comments_levels(self, context: ProcessingContext, limit: int) -> None:
        # Reduce non-doc comments progressively
        levels = [256, 128, 64, 32]
        for lvl in levels:
            cfg = CommentConfig(policy="keep_doc", max_tokens=lvl)
            CommentOptimizer(cfg, self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")
            if self.tok.count_text(context.raw_text or "") <= int(limit):
                break

    def _apply_function_bodies(self, context: ProcessingContext, *, mode: str) -> None:
        # mode in {"public_only", "non_public"}
        fb = FunctionBodyConfig(mode=mode, min_lines=1)  # type: ignore[arg-type]
        FunctionBodyOptimizer(fb, self.adapter).apply(context)

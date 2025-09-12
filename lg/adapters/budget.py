from __future__ import annotations

"""
Budget System controller (M7).

Applies stepwise, escalating optimizations until a per-file token budget is met.
Works on the ProcessingContext by temporarily disabling placeholders (style="none"),
committing edits between steps (commit-and-reseed), and recording basic telemetry.
"""

from typing import List

from .code_model import (
    CodeCfg,
    CommentConfig,
    ImportConfig,
    LiteralConfig,
    FunctionBodyConfig,
    ImportPolicy,
    FunctionBodyStrip,
    BudgetConfig,
)
from .context import ProcessingContext
from .optimizations import (
    ImportOptimizer,
    CommentOptimizer,
    LiteralOptimizer,
    FunctionBodyOptimizer,
    PublicApiOptimizer,
)


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
    def __init__(self, *, adapter, tokenizer, cfg_budget: BudgetConfig, cfg: CodeCfg):
        self.adapter = adapter
        self.tok = tokenizer
        self.cfg_budget = cfg_budget
        self.cfg = cfg

    def run(self, context: ProcessingContext) -> None:
        if not self.cfg_budget.max_tokens_per_file:
            return
        limit = int(self.cfg_budget.max_tokens_per_file)

        # Record initial tokens
        tokens_before = self.tok.count_text(context.raw_text or "")
        context.metrics.set(f"{self.adapter.name}.budget.tokens_before", tokens_before)
        if tokens_before <= limit:
            return

        original_placeholder_style = context.placeholders.placeholder_style
        # Disable placeholders during budget steps (pure deletions where applicable)
        context.placeholders.placeholder_style = "none"

        order = self.cfg_budget.priority_order or DEFAULT_ORDER
        tokens_prev = tokens_before

        for step in order:
            self._apply_step(step, context, limit)
            tokens_now = self.tok.count_text(context.raw_text or "")
            context.metrics.set(f"{self.adapter.name}.budget.steps.{step}", max(0, tokens_prev - tokens_now))
            tokens_prev = tokens_now

            if tokens_now <= limit:
                break

        # Final tokens
        tokens_after = self.tok.count_text(context.raw_text or "")
        context.metrics.set(f"{self.adapter.name}.budget.tokens_after", tokens_after)

        # Restore placeholder style for subsequent normal optimization and finalization
        context.placeholders.placeholder_style = original_placeholder_style

    # ---------------- internals ---------------- #

    def _apply_step(self, step: str, context: ProcessingContext, limit_int: int) -> None:
        if step == "imports_external":
            self._apply_imports(context, policy="strip_external")
        elif step == "imports_local":
            self._apply_imports(context, policy="strip_local")
        elif step == "literals":
            self._apply_literals_levels(context, limit_int)
        elif step == "comments":
            self._apply_comments_levels(context, limit_int)
        elif step == "private_bodies":
            self._apply_function_bodies(context, mode="non_public")
        elif step == "public_api_only":
            PublicApiOptimizer(self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")
        elif step == "public_bodies":
            # На всякий случай "all", вдруг "non_public" была ранее пропущена
            self._apply_function_bodies(context, mode="all")
        elif step == "docstrings_first_sentence":
            # Keep first sentence of documentation; non-doc comments may be removed
            CommentOptimizer("keep_first_sentence", self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")

    def _apply_imports(self, context: ProcessingContext, *, policy: ImportPolicy) -> None:
        cfg = ImportConfig(policy=policy, summarize_long=True)
        ImportOptimizer(cfg, self.adapter).apply(context)
        new_text, _ = context.editor.apply_edits()
        context.reseed(new_text, self.adapter, placeholder_style="none")

    def _apply_literals_levels(self, context: ProcessingContext, limit_int: int) -> None:
        # Conservative descending levels
        levels = [512, 256, 128, 64, 32]
        # If file is huge vs limit, start from min(limit//2, 512) roughly
        tokens_now = self.tok.count_text(context.raw_text or "")
        start_idx = 0
        if tokens_now > 0 and limit_int:
            # rough heuristic to skip too-loose levels
            for i, lvl in enumerate(levels):
                if lvl <= max(32, limit_int // 2):
                    start_idx = i
                    break
        for lvl in levels[start_idx:]:
            LiteralOptimizer(LiteralConfig(max_tokens=lvl), self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")
            if self.tok.count_text(context.raw_text or "") <= limit_int:
                break

    def _apply_comments_levels(self, context: ProcessingContext, limit_int: int) -> None:
        # Reduce non-doc comments progressively
        levels = [256, 128, 64, 32]
        for lvl in levels:
            cfg = CommentConfig(policy="keep_doc", max_tokens=lvl)
            CommentOptimizer(cfg, self.adapter).apply(context)
            new_text, _ = context.editor.apply_edits()
            context.reseed(new_text, self.adapter, placeholder_style="none")
            if self.tok.count_text(context.raw_text or "") <= limit_int:
                break

    def _apply_function_bodies(self, context: ProcessingContext, *, mode: FunctionBodyStrip) -> None:
        fb = FunctionBodyConfig(mode=mode)
        FunctionBodyOptimizer(fb, self.adapter).apply(context)
        new_text, _ = context.editor.apply_edits()
        context.reseed(new_text, self.adapter, placeholder_style="none")

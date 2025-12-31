"""
Rendering context for template engine.

Manages state during template processing, including active tags,
modes, and their overrides via {% mode %} blocks.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Set, List, Optional

from .addressing import AddressingContext
from .evaluator import TemplateConditionEvaluator
from ..config.adaptive_model import ModeOptions
from ..run_context import RunContext, ConditionContext


@dataclass
class TemplateState:
    """
    Snapshot of template state for saving/restoring.

    Used for implementing state stack when entering/exiting
    {% mode %} blocks.
    """
    mode_options: ModeOptions
    active_tags: Set[str]
    active_modes: Dict[str, str]  # modeset -> mode_name

    def copy(self) -> TemplateState:
        """Creates a deep copy of the state."""
        return TemplateState(
            mode_options=self.mode_options,
            active_tags=set(self.active_tags),
            active_modes=dict(self.active_modes)
        )


class TemplateContext:
    """
    Template rendering context with state management.

    Tracks active tags, modes, and their overrides during
    template processing. Maintains state stack for proper handling
    of nested {% mode %} blocks.
    """

    def __init__(self, run_ctx: RunContext):
        """
        Initializes the template context.

        Args:
            run_ctx: Execution context with base settings
        """
        self.run_ctx = run_ctx
        self.adaptive_loader = run_ctx.adaptive_loader

        # Current state (initialized from run_ctx)
        self.current_state = TemplateState(
            mode_options=run_ctx.mode_options,
            active_tags=set(run_ctx.active_tags),
            active_modes=dict(run_ctx.options.modes)
        )

        # State stack for nested mode blocks
        self.state_stack: List[TemplateState] = []

        # Cache of tag sets for condition evaluation
        self._tagsets_cache: Optional[Dict[str, Set[str]]] = None

        # Condition evaluator (created lazily)
        self._condition_evaluator: Optional[TemplateConditionEvaluator] = None

        # Unified addressing system - single entry point for all resource resolution
        self.addressing = AddressingContext(
            repo_root=run_ctx.root,
            initial_cfg_root=run_ctx.root / "lg-cfg",
            section_service=run_ctx.section_service
        )

    def get_condition_evaluator(self) -> TemplateConditionEvaluator:
        """
        Returns condition evaluator for current state.

        Creates new evaluator or updates existing one when state changes.
        """
        if self._condition_evaluator is None:
            self._condition_evaluator = self._create_condition_evaluator()
        else:
            # Update evaluator context when state changes
            condition_context = self._create_condition_context()
            self._condition_evaluator.update_context(condition_context)

        return self._condition_evaluator

    def enter_mode_block(self, modeset: str, mode: str) -> None:
        """
        Enters mode block {% mode modeset:mode %}.

        Saves current state and applies new mode,
        activating associated tags and options.

        Args:
            modeset: Name of mode set
            mode: Name of mode in the set

        Raises:
            ValueError: If mode not found in configuration
        """
        # Save current state to stack
        self.state_stack.append(self.current_state.copy())

        # Get mode information
        modes_config = self.adaptive_loader.get_modes_config()
        mode_set = modes_config.mode_sets.get(modeset)

        if not mode_set:
            raise ValueError(f"Unknown mode set '{modeset}'")

        mode_info = mode_set.modes.get(mode)
        if not mode_info:
            available_modes = list(mode_set.modes.keys())
            raise ValueError(
                f"Unknown mode '{mode}' in mode set '{modeset}'. "
                f"Available modes: {', '.join(available_modes)}"
            )

        # Apply new mode
        self.current_state.active_modes[modeset] = mode

        # Activate mode tags
        self.current_state.active_tags.update(mode_info.tags)

        # Update mode options
        self.current_state.mode_options = ModeOptions.merge_from_modes(
            modes_config,
            self.current_state.active_modes
        )

        # Reset condition evaluator cache
        self._condition_evaluator = None

    def exit_mode_block(self) -> None:
        """
        Exits mode block {% endmode %}.

        Restores previous state from stack.

        Raises:
            RuntimeError: If state stack is empty (no matching entry)
        """
        if not self.state_stack:
            raise RuntimeError("No mode block to exit (state stack is empty)")

        # Restore previous state
        self.current_state = self.state_stack.pop()

        # Reset condition evaluator cache
        self._condition_evaluator = None

    @contextmanager
    def file_scope(self, file_path: Path, new_origin: Optional[str] = None):
        """
        Context manager for file processing context.

        Updates current directory and optionally origin.

        Args:
            file_path: Path to the file being processed
            new_origin: New origin scope (if different from current)
        """
        self.addressing.push(file_path, new_origin)
        try:
            yield
        finally:
            self.addressing.pop()

    def get_origin(self) -> str:
        """
        Returns current origin from addressing context.

        Returns:
            Current origin ("self" for root scope or path to subdomain)
        """
        return self.addressing.origin

    def evaluate_condition(self, condition_ast) -> bool:
        """
        Evaluates condition in current context.

        Args:
            condition_ast: AST of condition to evaluate

        Returns:
            Result of condition evaluation
        """
        evaluator = self.get_condition_evaluator()
        return evaluator.evaluate(condition_ast)

    def evaluate_condition_text(self, condition_text: str) -> bool:
        """
        Evaluates condition from text representation.

        Args:
            condition_text: Text representation of condition

        Returns:
            Result of condition evaluation
        """
        evaluator = self.get_condition_evaluator()
        return evaluator.evaluate_condition_text(condition_text)

    def _create_condition_evaluator(self) -> TemplateConditionEvaluator:
        """Creates new condition evaluator for current state."""
        condition_context = self._create_condition_context()
        return TemplateConditionEvaluator(condition_context)

    def _create_condition_context(self) -> ConditionContext:
        """Creates condition context from current template state."""
        tagsets = self._get_tagsets()

        return ConditionContext(
            active_tags=self.current_state.active_tags,
            tagsets=tagsets,
            origin=self.addressing.origin,
            task_text=self.run_ctx.get_effective_task_text(),
        )

    def _get_tagsets(self) -> Dict[str, Set[str]]:
        """
        Returns map of tag sets.

        Caches result to avoid repeated loading.
        """
        if self._tagsets_cache is None:
            tags_config = self.adaptive_loader.get_tags_config()

            self._tagsets_cache = {}

            # Add tag sets
            for set_name, tag_set in tags_config.tag_sets.items():
                self._tagsets_cache[set_name] = set(tag_set.tags.keys())

            # Add global tags as separate set
            if tags_config.global_tags:
                self._tagsets_cache["global"] = set(tags_config.global_tags.keys())

        return self._tagsets_cache

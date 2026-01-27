"""
Rendering context for template engine.

Manages state during template processing, including active tags,
modes, and their overrides via {% mode %} blocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set, List, Optional, Tuple

from .evaluator import TemplateConditionEvaluator
from ..adaptive.model import ModeOptions, AdaptiveModel
from ..run_context import RunContext, ConditionContext
from ..adaptive.errors import InvalidModeReferenceError, UnknownModeSetError


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
    """

    def __init__(self, run_ctx: RunContext, adaptive_model: AdaptiveModel):
        """
        Initialize template context.

        Args:
            run_ctx: Runtime context
            adaptive_model: Resolved adaptive model for the target
        """
        self.run_ctx = run_ctx
        self.adaptive_model = adaptive_model

        # Validate CLI modes against model
        self._validate_cli_modes()

        # Compute state from CLI args and model
        active_tags, mode_options = self._compute_state_from_cli_and_model()

        self.current_state = TemplateState(
            mode_options=mode_options,
            active_tags=active_tags,
            active_modes=dict(self.run_ctx.options.modes)
        )

        self.state_stack: List[TemplateState] = []
        self._tagsets_cache: Optional[Dict[str, Set[str]]] = None
        self._condition_evaluator: Optional[TemplateConditionEvaluator] = None

    def _validate_cli_modes(self) -> None:
        """
        Validate CLI modes against the adaptive model.

        Raises:
            UnknownModeSetError: If mode set not found
            InvalidModeReferenceError: If mode not found in set
        """
        for modeset_id, mode_id in self.run_ctx.options.modes.items():
            mode_set = self.adaptive_model.get_mode_set(modeset_id)
            if not mode_set:
                available = list(self.adaptive_model.mode_sets.keys())
                raise UnknownModeSetError(
                    modeset_id=modeset_id,
                    available_sets=available,
                )

            if mode_id not in mode_set.modes:
                available_modes = list(mode_set.modes.keys())
                raise InvalidModeReferenceError(
                    modeset=modeset_id,
                    mode=mode_id,
                    available_modes=available_modes,
                )

    def _compute_state_from_cli_and_model(self) -> Tuple[Set[str], ModeOptions]:
        """
        Compute active tags and mode options from CLI args and model.

        Returns:
            Tuple of (active_tags, mode_options)
        """
        # Start with extra tags from CLI
        active_tags = set(self.run_ctx.options.extra_tags)

        # Add tags from active modes
        if self.adaptive_model:
            for modeset_id, mode_id in self.run_ctx.options.modes.items():
                mode_set = self.adaptive_model.get_mode_set(modeset_id)
                if mode_set:
                    mode = mode_set.get_mode(mode_id)
                    if mode:
                        active_tags.update(mode.tags)

        # Compute mode options
        mode_options = self._compute_mode_options()

        return active_tags, mode_options

    def _compute_mode_options(self) -> ModeOptions:
        """
        Compute ModeOptions from active modes.

        Returns:
            ModeOptions with merged settings from all active modes
        """
        result = ModeOptions()

        if not self.adaptive_model:
            return result

        for modeset_id, mode_id in self.run_ctx.options.modes.items():
            mode_set = self.adaptive_model.get_mode_set(modeset_id)
            if not mode_set:
                continue
            mode = mode_set.get_mode(mode_id)
            if not mode:
                continue

            # vcs_mode from modes (last non-default wins)
            if mode.vcs_mode != "all":
                result.vcs_mode = mode.vcs_mode

        return result

    def get_effective_task_text(self) -> Optional[str]:
        """
        Return effective task text considering priorities.

        Priority:
        1. Explicitly specified --task (if not empty)
        2. Tasks from active modes (combined through paragraphs)
        3. None if neither is specified

        Returns:
            Effective task text or None
        """
        # Priority 1: explicitly specified --task
        if self.run_ctx.options.task_text and self.run_ctx.options.task_text.strip():
            return self.run_ctx.options.task_text

        # Priority 2: tasks from active modes
        mode_tasks = self._collect_mode_tasks()
        if mode_tasks:
            return "\n\n".join(mode_tasks)

        return None

    def _collect_mode_tasks(self) -> List[str]:
        """
        Collect default_task from all active modes.

        Returns:
            List of non-empty tasks from modes (sorted by modeset name for determinism)
        """
        if not self.adaptive_model:
            return []

        tasks = []

        # Sort by modeset name for determinism
        for modeset_id in sorted(self.run_ctx.options.modes.keys()):
            mode_id = self.run_ctx.options.modes[modeset_id]

            mode_set = self.adaptive_model.get_mode_set(modeset_id)
            if not mode_set:
                continue

            mode = mode_set.get_mode(mode_id)
            if not mode or not mode.default_task:
                continue

            tasks.append(mode.default_task)

        return tasks

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

        Validates against the adaptive model, saves current state,
        and applies new mode with associated tags and options.

        Args:
            modeset: Name of mode set
            mode: Name of mode in the set

        Raises:
            InvalidModeReferenceError: If mode not found in context's model
        """
        # Save current state to stack
        self.state_stack.append(self.current_state.copy())

        # Validate against adaptive model
        mode_set = self.adaptive_model.get_mode_set(modeset)
        if not mode_set:
            available = list(self.adaptive_model.mode_sets.keys())
            raise InvalidModeReferenceError(
                modeset=modeset,
                mode=mode,
                available_modes=available
            )

        mode_info = mode_set.get_mode(mode)
        if not mode_info:
            available_modes = list(mode_set.modes.keys())
            raise InvalidModeReferenceError(
                modeset=modeset,
                mode=mode,
                available_modes=available_modes
            )

        # Apply new mode
        self.current_state.active_modes[modeset] = mode

        # Activate mode tags
        self.current_state.active_tags.update(mode_info.tags)

        # Update mode options
        self.current_state.mode_options = self._compute_mode_options()

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

    def get_origin(self) -> str:
        """
        Returns current origin from addressing context.

        Returns:
            Current origin ("self" for root scope or path to subdomain)
        """
        return self.run_ctx.addressing.origin

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

        # Compute normalized provider base-id
        provider_base = None
        if self.run_ctx.options.provider:
            from ..run_context import normalize_provider_id
            provider_base = normalize_provider_id(self.run_ctx.options.provider)

        return ConditionContext(
            active_tags=self.current_state.active_tags,
            tagsets=tagsets,
            origin=self.run_ctx.addressing.origin,
            task_text=self.get_effective_task_text(),
            provider_base_id=provider_base,
        )

    def _get_tagsets(self) -> Dict[str, Set[str]]:
        """
        Returns map of tag sets from the adaptive model.

        Caches result to avoid repeated computation.
        """
        if self._tagsets_cache is None:
            self._tagsets_cache = {}

            if self.adaptive_model:
                for set_id, tag_set in self.adaptive_model.tag_sets.items():
                    self._tagsets_cache[set_id] = set(tag_set.tags.keys())

        return self._tagsets_cache

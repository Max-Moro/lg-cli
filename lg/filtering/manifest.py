"""
Builder of manifest for a single section.

Takes into account the active template context (modes, tags, conditions).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Set, cast, Optional

from .filters import FilterEngine
from .fs import iter_files
from .model import FilterNode
from ..adapters.registry import get_adapter_for_path
from ..section import SectionCfg, AdapterConfig, EmptyPolicy
from ..config.paths import is_cfg_relpath
from ..rendering import get_language_for_file
from ..template.context import TemplateContext
from ..addressing.types import ResolvedSection
from ..types import FileEntry, SectionManifest
from ..git import VcsProvider, NullVcs
from ..git.gitignore import GitIgnoreService


def build_section_manifest(
    resolved: ResolvedSection,
    section_config: SectionCfg,
    template_ctx: TemplateContext,
    root: Path,
    vcs: VcsProvider,
    gitignore_service: Optional[GitIgnoreService],
    vcs_mode: str,
    target_branch: Optional[str] = None
) -> SectionManifest:
    """
    Builds a section manifest based on a ready configuration (for virtual sections).

    Args:
        resolved: Resolved section
        section_config: Ready section configuration
        template_ctx: Template context with active modes/tags
        root: Repository root
        vcs: VCS provider
        gitignore_service: GitIgnore service for filtering ignored files
        vcs_mode: VCS mode ("all", "changes" or "branch-changes")
        target_branch: Target branch for "branch-changes" mode (optional)

    Returns:
        Section manifest with filtered files
    """
    vcs = vcs or NullVcs()

    # Create base filter with conditional additions
    filter_engine = _create_enhanced_filter_engine(section_config, template_ctx)

    # Compute final adapter options considering conditions
    adapters_cfg = _compute_final_adapter_configs(section_config, template_ctx)

    # Determine if section describes local files
    is_local_files = _is_gitignored_section(section_config, gitignore_service, resolved.scope_rel)

    # Preliminary check: determine if section is documentation-only
    # Collect files with vcs_mode: all to check section type
    preview_files = _collect_section_files(
        resolved=resolved,
        section_cfg=section_config,
        filter_engine=filter_engine,
        changed_files=set(),  # empty set = all files when vcs_mode == "all"
        vcs_mode="all",
        root=root,
        adapters_cfg=adapters_cfg,
        is_local_files=is_local_files,
        gitignore_service=gitignore_service,
        template_ctx=template_ctx
    )

    # Determine if section is documentation-only
    is_doc_only = _is_doc_only_section(preview_files)

    # For doc-only sections, force vcs_mode: all
    effective_vcs_mode = "all" if is_doc_only else vcs_mode

    # Get changed files depending on effective VCS mode
    changed: Set[str] = set()
    if effective_vcs_mode == "changes":
        changed = vcs.changed_files(root)
    elif effective_vcs_mode == "branch-changes":
        changed = vcs.branch_changed_files(root, target_branch)

    # Collect final file set
    if effective_vcs_mode == "all":
        # Reuse preview result if mode didn't change
        files = preview_files
    else:
        # Rebuild with VCS filtering applied
        files = _collect_section_files(
            resolved=resolved,
            section_cfg=section_config,
            filter_engine=filter_engine,
            changed_files=changed,
            vcs_mode=effective_vcs_mode,
            root=root,
            adapters_cfg=adapters_cfg,
            is_local_files=is_local_files,
            gitignore_service=gitignore_service,
            template_ctx=template_ctx
        )

    # Create manifest
    return SectionManifest(
        resolved=resolved,
        files=files,
        path_labels=section_config.path_labels,
        adapters_cfg=adapters_cfg,
        is_doc_only=is_doc_only,
        is_local_files=is_local_files
    )


def _compute_final_adapter_configs(section_cfg: SectionCfg, template_ctx: TemplateContext) -> Dict[str, Dict]:
    """
    Computes final adapter options considering conditional rules.

    Args:
        section_cfg: Section configuration with AdapterConfig objects
        template_ctx: Template context with active tags

    Returns:
        Dictionary of final adapter options (adapter_name -> options)
    """
    return {
        adapter_name: _resolve_adapter_config(adapter_config, template_ctx)
        for adapter_name, adapter_config in section_cfg.adapters.items()
    }


def _resolve_adapter_config(adapter_config: AdapterConfig, template_ctx: TemplateContext) -> Dict[str, object]:
    """
    Resolves a single AdapterConfig into a flat options dict.

    Evaluates conditional options (when: blocks) and merges them
    on top of base options in definition order.

    Args:
        adapter_config: Adapter configuration with optional conditions
        template_ctx: Template context for condition evaluation

    Returns:
        Flat dictionary of resolved adapter options
    """
    final = dict(adapter_config.base_options)
    for cond_opt in adapter_config.conditional_options:
        if template_ctx.evaluate_condition_text(cond_opt.condition):
            final.update(cond_opt.options)
    return final


def _is_doc_only_section(files: List[FileEntry]) -> bool:
    """
    Determines if a section is documentation-only.

    A section is considered documentation-only if all its files have language_hint
    in ('markdown', '') - i.e., markdown or plain text.

    Args:
        files: List of section files

    Returns:
        True if section contains only markdown/plain text files
    """
    if not files:
        return False

    return all(f.language_hint in ("markdown", "") for f in files)


def _create_enhanced_filter_engine(section_cfg: SectionCfg, template_ctx: TemplateContext) -> FilterEngine:
    """
    Creates a filtering engine considering conditional filters from template context.

    Recursively applies active conditional filters to all FilterNode nodes,
    adding additional allow/block rules when conditions are met.
    """
    # Start with the section's base filter
    base_filter = section_cfg.filters

    # Recursively apply conditional filters to all nodes
    enhanced_filter = _apply_conditional_filters_recursive(base_filter, template_ctx)

    return FilterEngine(enhanced_filter)


def _apply_conditional_filters_recursive(node: FilterNode, template_ctx: TemplateContext) -> FilterNode:
    """
    Recursively applies conditional filters to a node and all its child nodes.

    Args:
        node: Source filtering node
        template_ctx: Template context for condition evaluation

    Returns:
        New node with applied conditional filters
    """
    import logging

    # Create a copy of the node with base rules
    enhanced_node = FilterNode(
        mode=node.mode,
        allow=list(node.allow),
        block=list(node.block),
        conditional_filters=list(node.conditional_filters),  # Keep for information
        children={}  # Will fill later
    )

    # Apply conditional filters of current node
    for conditional_filter in node.conditional_filters:
        try:
            # Evaluate condition in template context
            condition_met = template_ctx.evaluate_condition_text(conditional_filter.condition)

            if condition_met:
                # Add additional filtering rules
                enhanced_node.allow.extend(conditional_filter.allow)
                enhanced_node.block.extend(conditional_filter.block)
        except Exception as e:
            # Log condition evaluation error, but do not interrupt processing
            logging.warning(
                f"Failed to evaluate conditional filter condition '{conditional_filter.condition}': {e}"
            )

    # Recursively process child nodes
    for child_name, child_node in node.children.items():
        enhanced_node.children[child_name] = _apply_conditional_filters_recursive(child_node, template_ctx)

    return enhanced_node


def _is_gitignored_section(
    section_cfg: SectionCfg,
    gitignore_service: Optional[GitIgnoreService],
    scope_rel: str
) -> bool:
    """
    Determines if section's allow patterns are covered by .gitignore.

    Args:
        section_cfg: Section configuration
        gitignore_service: GitIgnore service for checking patterns
        scope_rel: Section scope relative to root (empty for root scope)

    Returns:
        True if all allow patterns are covered by .gitignore
    """
    root_filter = section_cfg.filters

    # Must be in allow mode
    if root_filter.mode != "allow":
        return False

    # Must have allow patterns
    if not root_filter.allow:
        return False

    # No gitignore service means no .git directory
    if gitignore_service is None:
        return False

    # Check if all allow patterns are covered by gitignore
    for pattern in root_filter.allow:
        pattern_normalized = pattern.lstrip('/')

        # Prepend scope_rel to get path relative to root
        if scope_rel:
            full_path = f"{scope_rel}/{pattern_normalized}"
        else:
            full_path = pattern_normalized

        if not gitignore_service.is_ignored(full_path):
            return False

    # All patterns are covered by gitignore
    return True

def _collect_section_files(
    resolved: ResolvedSection,
    section_cfg: SectionCfg,
    filter_engine: FilterEngine,
    changed_files: Set[str],
    vcs_mode: str,
    root: Path,
    adapters_cfg: dict[str, dict],
    is_local_files: bool,
    gitignore_service: Optional[GitIgnoreService],
    template_ctx: TemplateContext
) -> List[FileEntry]:
    """
    Collects files for a section with all filters applied.
    """
    scope_rel = resolved.scope_rel

    # Function to check if a file belongs to the section's scope
    def in_scope(path_posix: str) -> bool:
        if scope_rel == "":
            return True
        return path_posix == scope_rel or path_posix.startswith(f"{scope_rel}/")

    def rel_for_engine(path_posix: str) -> str:
        """Path relative to scope_dir for applying section filters."""
        if scope_rel == "":
            return path_posix
        return path_posix[len(scope_rel):].lstrip("/")

    # File extensions
    extensions = {e.lower() for e in section_cfg.extensions}

    # GitIgnore service - skip for local files sections
    # Local files sections (all patterns covered by .gitignore) represent
    # deliberate inclusion of specific files (e.g., local configs, workspace docs)
    # that should bypass .gitignore
    effective_gitignore = None if is_local_files else gitignore_service

    # Prepare target rules for targeted overrides
    target_specs = _prepare_target_specs(section_cfg)

    # Pruner for early directory pruning
    def _pruner(rel_dir: str) -> bool:
        """Decide whether to descend into directory rel_dir (repo-root relative, POSIX)."""
        if scope_rel == "":
            # Global scope (repo root): apply filters everywhere
            sub_rel = rel_dir
            if is_cfg_relpath(sub_rel):
                # For virtual sections check if filter can include lg-cfg files
                # If allow has paths starting with /lg-cfg/, allow descent
                return filter_engine.may_descend(sub_rel)
            return filter_engine.may_descend(sub_rel)

        if rel_dir == "":
            # repo root - always can descend
            return True

        is_ancestor_of_scope = scope_rel.startswith(rel_dir + "/") or scope_rel == rel_dir
        is_inside_scope = rel_dir.startswith(scope_rel + "/") or rel_dir == scope_rel

        if not (is_ancestor_of_scope or is_inside_scope):
            # Branch is definitely not of interest to this section
            return False

        if is_ancestor_of_scope and not is_inside_scope:
            # We are above scope_rel: section filters not yet applicable
            return True

        # We are within scope_rel: apply section filters
        sub_rel = rel_for_engine(rel_dir)
        if is_cfg_relpath(sub_rel):
            # For virtual sections check if filter can include lg-cfg files
            # If allow has paths starting with /lg-cfg/, allow descent
            return filter_engine.may_descend(sub_rel)
        return filter_engine.may_descend(sub_rel)

    # Collect files
    files: List[FileEntry] = []

    for fp in iter_files(root, extensions=extensions, gitignore_service=effective_gitignore, dir_pruner=_pruner):
        rel_posix = fp.resolve().relative_to(root.resolve()).as_posix()

        # Filter by VCS mode
        if vcs_mode in ("changes", "branch-changes") and rel_posix not in changed_files:
            continue

        # Restrict to files within scope_rel
        if not in_scope(rel_posix):
            continue

        # Apply section filters
        rel_engine = rel_for_engine(rel_posix)
        if not filter_engine.includes(rel_engine):
            continue

        # Handle empty files
        if _should_skip_empty_file(fp, bool(section_cfg.skip_empty), adapters_cfg):
            continue

        # Determine file language
        lang = get_language_for_file(fp)

        # Determine targeted adapter overrides
        overrides = _calculate_adapter_overrides(rel_engine, target_specs, template_ctx)

        # Create FileEntry
        files.append(FileEntry(
            abs_path=fp,
            rel_path=rel_posix,
            language_hint=lang,
            adapter_overrides=overrides
        ))

    # Sort by rel_path for stability
    files.sort(key=lambda f: f.rel_path)

    return files


def _prepare_target_specs(section_cfg: SectionCfg) -> List[tuple]:
    """
    Prepares target specifications with specificity metric.
    """
    target_specs = []
    for idx, target_rule in enumerate(section_cfg.targets):
        # Simple specificity metric: sum of string lengths without '*' and '?'
        pat_clean_len = sum(len(p.replace("*", "").replace("?", "")) for p in target_rule.match)
        target_specs.append((pat_clean_len, idx, target_rule.match, target_rule.adapter_cfgs))

    return target_specs


def _should_skip_empty_file(file_path: Path, effective_exclude_empty: bool, adapters_cfg: dict[str, dict]) -> bool:
    """
    Determines whether to skip an empty file.

    Considers section and adapter policies considering conditional rules.
    """
    try:
        size0 = (file_path.stat().st_size == 0)
    except Exception:
        size0 = False

    if not size0:
        return False  # File is not empty

    # Determine adapter and its policy
    adapter_cls = get_adapter_for_path(file_path)

    # Check adapter policy
    raw_cfg = adapters_cfg.get(adapter_cls.name)
    if raw_cfg and "empty_policy" in raw_cfg:
        empty_policy = cast(EmptyPolicy, raw_cfg["empty_policy"])

        if empty_policy == "include":
            effective_exclude_empty = False
        elif empty_policy == "exclude":
            effective_exclude_empty = True

    return effective_exclude_empty


def _calculate_adapter_overrides(
    rel_path: str,
    target_specs: List[tuple],
    template_ctx: TemplateContext
) -> Dict[str, dict]:
    """
    Calculates targeted adapter configuration overrides.

    Evaluates when: conditions in target adapter configs
    using the current template context.
    """
    overrides: Dict[str, dict] = {}

    # Sort by specificity, then by index
    for _spec_len, _idx, patterns, acfgs in sorted(target_specs, key=lambda x: (x[0], x[1])):
        matched = False
        for pat in patterns:
            # Normalize pattern to relative style
            pat_rel = pat.lstrip("/")
            if fnmatch.fnmatch(rel_path, pat_rel):
                matched = True
                break

        if not matched:
            continue

        # Apply shallow-merge by adapter names (resolve conditions first)
        for adapter_name, adapter_cfg in acfgs.items():
            resolved = _resolve_adapter_config(adapter_cfg, template_ctx)
            base = overrides.get(adapter_name, {})
            merged = dict(base)
            merged.update(resolved)
            overrides[adapter_name] = merged

    return overrides

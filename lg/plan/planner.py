from __future__ import annotations

from typing import List, Tuple

from ..paths import build_labels
from ..run_context import RunContext
from ..types import Manifest, Group, LangName, LANG_NONE, SectionPlan, ContextPlan, PathLabelMode


def _consecutive_groups_by_lang(entries: list, langs: list[LangName]) -> List[Tuple[LangName, List]]:
    """
    Разбить последовательность файлов на подпоследовательности одинакового языка,
    сохраняя порядок появления. (Аналог itertools.groupby, но без зависимости.)
    """
    out: List[Tuple[LangName, List]] = []
    if not entries:
        return out
    cur_lang = langs[0]
    bucket: List = [entries[0]]
    for e, lg in zip(entries[1:], langs[1:]):
        if lg == cur_lang:
            bucket.append(e)
        else:
            out.append((cur_lang, bucket))
            cur_lang = lg
            bucket = [e]
    out.append((cur_lang, bucket))
    return out


def _build_section_plan(
    sec_name: str,
    entries,
    langs: List[LangName],
    *,
    code_fence: bool,
    path_labels: PathLabelMode,
    run_ctx: RunContext,
    adapters_cfg: dict[str, dict]
) -> SectionPlan:
    """
    Строит план ТОЛЬКО для одной секции с учётом локальной политики code_fence.
    """
    md_only = all(l == "" for l in langs)
    # Глобальная опция может оверрайдить, но секционная политика тоже учитывается.
    use_fence = (run_ctx.options.code_fence and code_fence) and not md_only

    groups: List[Group] = []
    if use_fence:
        for lang, chunk in _consecutive_groups_by_lang(entries, langs):
            groups.append(Group(lang=lang, entries=chunk, mixed=False))
    else:
        mixed = len(set(langs)) > 1
        groups.append(Group(lang=LANG_NONE, entries=list(entries), mixed=mixed))

    # Вычисление меток (файловых разделителей)
    rels_in_order: List[str] = []
    for g in groups:
        for e in g.entries:
            rels_in_order.append(e.rel_path)
    labels_map = build_labels(rels_in_order, mode=path_labels)

    return SectionPlan(
        section=sec_name,
        md_only=md_only,
        use_fence=use_fence,
        groups=groups,
        labels=labels_map,
        adapters_cfg = adapters_cfg,
    )


def build_plan(manifest: Manifest, run_ctx: RunContext) -> ContextPlan:
    """
    Manifest → ContextPlan (список секционных Plan).
    Группировка выполняется ВНУТРИ каждой секции независимо.
    """
    # Быстрый выход, если секций нет
    any_section = next(manifest.iter_sections(), None)
    if not any_section:
        return ContextPlan(sections=[])

    # Сохраняем порядок появления секций по Manifest.
    sections_out: List[SectionPlan] = []
    for sec in manifest.iter_sections():
        entries = sec.files
        langs: List[LangName] = [f.language_hint for f in entries]

        sec_plan = _build_section_plan(
            sec_name=sec.id.as_key(),
            entries=entries,
            langs=langs,
            code_fence=sec.meta.code_fence,
            path_labels=sec.meta.path_labels,
            run_ctx=run_ctx,
            adapters_cfg=sec.adapters_cfg,
        )
        sections_out.append(sec_plan)

    return ContextPlan(sections=sections_out)

from __future__ import annotations

from typing import List, Tuple, Dict

from ..paths import build_labels
from ..run_context import RunContext
from ..types import Manifest, Group, LangName, SectionPlan, ContextPlan, SectionPlanCfg


def _lang_of(rel_lang: str | None) -> LangName:
    # В манифесте language_hint уже нормализован; пустая строка — markdown/plaintext
    return rel_lang or ""


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
    sec_cfg: SectionPlanCfg,
    run_ctx: RunContext
) -> SectionPlan:
    """
    Строит план ТОЛЬКО для одной секции с учётом локальной политики code_fence.
    """
    md_only = all(l == "" for l in langs)
    # Глобальная опция может оверрайдить, но секционная политика тоже учитывается.
    use_fence = (run_ctx.options.code_fence and sec_cfg.code_fence) and not md_only

    groups: List[Group] = []
    if use_fence:
        for lang, chunk in _consecutive_groups_by_lang(entries, langs):
            groups.append(Group(lang=lang, entries=chunk, mixed=False))
    else:
        mixed = len(set(langs)) > 1
        groups.append(Group(lang="", entries=list(entries), mixed=mixed))

    # Вычисление меток (файловых разделителей)
    rels_in_order: List[str] = []
    for g in groups:
        for e in g.entries:
            rels_in_order.append(e.rel_path)
    labels_map = build_labels(rels_in_order, mode=sec_cfg.path_labels)

    return SectionPlan(section=sec_name, md_only=md_only, use_fence=use_fence, groups=groups, labels=labels_map)


def build_plan(manifest: Manifest, run_ctx: RunContext) -> ContextPlan:
    """
    Manifest → ContextPlan (список секционных Plan).
    Группировка выполняется ВНУТРИ каждой секции независимо.
    """
    files = manifest.files
    if not files:
        return ContextPlan(sections=[])

    # Сохраняем порядок появления секций по Manifest.
    by_section: Dict[str, List] = {}
    order: List[str] = []
    for fr in files:
        if fr.section not in by_section:
            by_section[fr.section] = []
            order.append(fr.section)
        by_section[fr.section].append(fr)

    sections_out: List[SectionPlan] = []
    for sec_name in order:
        entries = by_section[sec_name]
        langs: List[LangName] = [_lang_of(f.language_hint) for f in entries]
        # Берём hints из Manifest; для «чужих» секций они уже там.
        sec_cfg_hint: SectionPlanCfg | None = manifest.sections_cfg.get(sec_name)
        sec_plan = _build_section_plan(sec_name, entries, langs, sec_cfg=sec_cfg_hint, run_ctx=run_ctx)
        sections_out.append(sec_plan)

    return ContextPlan(sections=sections_out)

from __future__ import annotations

from typing import List, Tuple, Dict

from ..config import SectionCfg
from ..types import Manifest, Group, LangName, SectionPlan, ContextPlan


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
    sec_cfg: SectionCfg,
    run_ctx
) -> SectionPlan:
    """
    Строит план ТОЛЬКО для одной секции с учётом локальной политики code_fence.
    """
    md_only = all(l == "" for l in langs)
    # Глобальная опция может оверрайдить, но секционная политика тоже учитывается.
    opt_fence = bool(getattr(run_ctx, "options").code_fence)
    sec_fence = bool(sec_cfg.code_fence)
    use_fence = (opt_fence and sec_fence) and not md_only

    groups: List[Group] = []
    if use_fence:
        for lang, chunk in _consecutive_groups_by_lang(entries, langs):
            groups.append(Group(lang=lang, entries=chunk, mixed=False))
    else:
        mixed = len(set(langs)) > 1
        groups.append(Group(lang="", entries=list(entries), mixed=mixed))

    return SectionPlan(section=sec_name, md_only=md_only, use_fence=use_fence, groups=groups)


def build_plan(manifest: Manifest, run_ctx) -> ContextPlan:
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
    sections_cfg = getattr(run_ctx, "config").sections
    for sec_name in order:
        entries = by_section[sec_name]
        langs: List[LangName] = [_lang_of(f.language_hint) for f in entries]
        sec_cfg: SectionCfg = sections_cfg.get(sec_name)  # type: ignore[assignment]
        sec_plan = _build_section_plan(sec_name, entries, langs, sec_cfg=sec_cfg, run_ctx=run_ctx)
        sections_out.append(sec_plan)

    return ContextPlan(sections=sections_out)

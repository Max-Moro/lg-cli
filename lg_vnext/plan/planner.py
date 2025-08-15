from __future__ import annotations

from typing import List, Tuple

from ..types import Manifest, Plan, Group, LangName


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


def build_plan(manifest: Manifest, run_ctx) -> Plan:
    """
    Manifest → Plan (md_only, use_fence, groups).
    Правила:
      • md_only: все файлы с пустым language_hint (markdown/plaintext).
      • use_fence: run_ctx.options.code_fence and not md_only.
      • При use_fence=True — группируем подряд идущие файлы одного языка.
      • При use_fence=False — один «смешанный» блок; mixed=True если языков > 1.
    Стабильность порядка обеспечивается предварительной сортировкой Manifest.
    """
    files = manifest.files
    if not files:
        return Plan(md_only=True, use_fence=False, groups=[])

    langs: List[LangName] = [_lang_of(f.language_hint) for f in files]
    md_only = all(l == "" for l in langs)

    use_fence = bool(getattr(run_ctx, "options").code_fence) and not md_only

    groups: List[Group] = []
    if use_fence:
        for lang, chunk in _consecutive_groups_by_lang(files, langs):
            groups.append(Group(lang=lang, entries=chunk, mixed=False))
    else:
        mixed = len(set(langs)) > 1
        groups.append(Group(lang="", entries=list(files), mixed=mixed))

    return Plan(md_only=md_only, use_fence=use_fence, groups=groups)

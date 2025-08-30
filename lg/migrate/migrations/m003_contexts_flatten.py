from __future__ import annotations

import re
from pathlib import Path
from typing import Set

from ..fs import CfgFs


class _M003_ContextsFlatten:
    """
    Миграция №3:
      • Переносим ВСЕ *.md из lg-cfg/contexts/** → lg-cfg/** (с сохранением поддиректорий относительно contexts/).
      • Классифицируем файлы:
          – если файл упоминается как `${tpl:<resource>}` хотя бы в одном документе текущего lg-cfg → шаблон (*.tpl.md);
          – иначе → считаем контекстом (*.ctx.md).
      • Плейсхолдеры НЕ переписываем.
      • Конфликты по месту назначения:
          – если содержимое совпадает → удаляем исходник;
          – иначе → переносим как `<name>.from-contexts(.N).tpl.md` или `.ctx.md`.
      • Идемпотентно.
    """
    id = 3
    title = "Flatten lg-cfg/contexts/** → lg-cfg/** with smart suffix (.tpl/.ctx) by usage"

    # Ровно та же семантика токенов, что и в TemplateTokens: ${...} и $...
    _PH_RE = re.compile(
        r"""
        \$\{
            (?P<braced>[A-Za-z0-9_@:/\-\[\]\.]+)
        \}
        |
        \$
            (?P<name>[A-Za-z0-9_@:/\-\[\]\.]+)
        """,
        re.VERBOSE,
    )

    def probe(self, fs: CfgFs) -> bool:
        # Сработает только если есть что переносить
        md_files = fs.glob_rel("contexts/**/*.md")
        if not md_files:
            md_files = fs.glob_rel("contexts/*.md")
        return bool(md_files)

    # ---------- helpers ----------
    @staticmethod
    def _resource_name(src_rel: str) -> str:
        """
        'contexts/foo/bar.tpl.md' → 'foo/bar'
        """
        assert src_rel.startswith("contexts/")
        tail = src_rel[len("contexts/") :]
        p = Path(tail)
        name = p.name
        if name.endswith(".tpl.md"):
            stem = name[: -len(".tpl.md")]
        elif name.endswith(".ctx.md"):
            stem = name[: -len(".ctx.md")]
        elif name.endswith(".md"):
            stem = name[: -len(".md")]
        else:
            stem = p.stem
        return str(p.with_name(stem).as_posix())

    @staticmethod
    def _dst_for(resource: str, is_tpl: bool) -> str:
        """
        resource='foo/bar' → 'foo/bar.tpl.md' | 'foo/bar.ctx.md'
        """
        suffix = ".tpl.md" if is_tpl else ".ctx.md"
        return str(Path(resource).with_suffix(suffix).as_posix())

    @staticmethod
    def _with_variant(rel: str, n: int) -> str:
        p = Path(rel)
        name = p.name
        if name.endswith(".tpl.md"):
            base = name[: -len(".tpl.md")]
            tail = ".tpl.md"
        elif name.endswith(".ctx.md"):
            base = name[: -len(".ctx.md")]
            tail = ".ctx.md"
        elif name.endswith(".md"):
            base = name[: -len(".md")]
            tail = ".md"
        else:
            base = p.stem
            tail = p.suffix
        extra = ".from-contexts" if n == 1 else f".from-contexts-{n}"
        new_name = f"{base}{extra}{tail}"
        return str(p.with_name(new_name).as_posix())

    def _collect_tpl_usages(self, fs: CfgFs) -> Set[str]:
        """
        Парсим ВСЕ *.md под текущим lg-cfg/ и собираем ресурсы, встречающиеся как ${tpl:...}.
        Учитываем только локальные формы ('tpl:...'), адресные ('tpl@...') пропускаем.
        Возвращаем набор resource-имен (с поддиректориями).
        """
        used_as_tpl: Set[str] = set()
        for rel in fs.glob_rel("**/*.md"):
            # Игнорируем всё, что под contexts/ — эти файлы мы и так переносим,
            # но их содержимое тоже может ссылаться на tpl — учитывать можно (и полезно).
            text = fs.read_text(rel)
            for m in self._PH_RE.finditer(text):
                token = m.group("braced") or m.group("name") or ""
                if not token or token.startswith("tpl@"):
                    continue
                if token.startswith("tpl:"):
                    res = token[len("tpl:") :].strip()
                    if res:
                        used_as_tpl.add(res)
        return used_as_tpl

    def apply(self, fs: CfgFs) -> None:
        # 1) Собираем все кандидаты под перенос
        src_files = fs.glob_rel("contexts/**/*.md")
        src_files += [rel for rel in fs.glob_rel("contexts/*.md") if rel not in src_files]
        if not src_files:
            return

        # 2) Сканируем использование ${tpl:...} во ВСЕХ md файлах текущего lg-cfg/
        used_as_tpl = self._collect_tpl_usages(fs)

        # 3) Переносим каждый файл по классификации
        for src_rel in src_files:
            resource = self._resource_name(src_rel)
            is_tpl = resource in used_as_tpl
            dst_rel = self._dst_for(resource, is_tpl=is_tpl)

            if fs.exists(dst_rel):
                try:
                    src_text = fs.read_text(src_rel)
                    dst_text = fs.read_text(dst_rel)
                except Exception:
                    src_text = ""
                    dst_text = None
                if dst_text is not None and src_text == dst_text:
                    # Совпадает — просто удалить исходник
                    fs.remove_file(src_rel)
                    continue
                # Ищем свободный вариант с .from-contexts(-N)
                n = 1
                alt_rel = self._with_variant(dst_rel, n)
                while fs.exists(alt_rel):
                    n += 1
                    alt_rel = self._with_variant(dst_rel, n)
                fs.move_atomic(src_rel, alt_rel)
                continue

            # Обычный перенос
            fs.move_atomic(src_rel, dst_rel)

        # 4) Если contexts/ опустела — удалим хвост
        if not fs.dir_has_files("contexts"):
            fs.remove_dir_tree("contexts")


MIGRATION = _M003_ContextsFlatten()

__all__ = ["MIGRATION"]
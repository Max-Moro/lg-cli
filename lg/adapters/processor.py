"""
Процессор файлов.

Обработка файлов через языковые адаптеры.
"""

from __future__ import annotations

from typing import Dict, List, cast

from ..adapters.base import BaseAdapter
from ..adapters.context import LightweightContext
from ..adapters.registry import get_adapter_for_path
from ..filtering.fs import read_text
from ..template.context import TemplateContext
from ..types import ProcessedFile, SectionPlan


def process_files(plan: SectionPlan, template_ctx: TemplateContext) -> List[ProcessedFile]:
    """
    Обрабатывает файлы через языковые адаптеры.
    
    Args:
        plan: План секции с файлами для обработки
        template_ctx: Контекст шаблона с настройками и сервисами
        
    Returns:
        Список обработанных файлов
    """
    processed_files = []
    cache = template_ctx.run_ctx.cache
    
    # Кэш связанных адаптеров для эффективности
    bound_cache: Dict[tuple[str, tuple[tuple[str, object], ...]], BaseAdapter] = {}
    
    for group in plan.groups:
        group_size = len(group.entries)
        
        for file_entry in group.entries:
            fp = file_entry.abs_path
            adapter_cls = get_adapter_for_path(fp)
            
            # Получаем конфигурацию адаптера (секционная + оверрайды)
            sec_raw_cfg = plan.manifest.adapters_cfg.get(adapter_cls.name)
            override_cfg = file_entry.adapter_overrides.get(adapter_cls.name)
            
            raw_cfg = None
            if sec_raw_cfg or override_cfg:
                raw_cfg = dict(sec_raw_cfg or {})
                raw_cfg.update(dict(override_cfg or {}))
            
            # Создаем или получаем связанный адаптер
            cfg_key = _freeze_cfg(raw_cfg or {})
            bkey = (adapter_cls.name, cfg_key)
            adapter = bound_cache.get(bkey)
            if adapter is None:
                adapter = adapter_cls.bind(raw_cfg, template_ctx.run_ctx.tokenizer)
                bound_cache[bkey] = adapter
            
            # Type casting для корректной типизации
            adapter = cast(BaseAdapter, adapter)
            
            # Читаем содержимое файла
            raw_text = read_text(fp)
            
            # Создаем контекст для адаптера
            lightweight_ctx = LightweightContext(
                file_path=fp,
                raw_text=raw_text,
                group_size=group_size,
                mixed=bool(group.mixed),
                template_ctx=template_ctx
            )
            
            # Проверяем эвристики пропуска
            if adapter.name != "base" and adapter.should_skip(lightweight_ctx):
                continue
            
            # Строим ключи кэша
            k_proc, p_proc = cache.build_processed_key(
                abs_path=fp,
                adapter_cfg=raw_cfg,
                active_tags=template_ctx.current_state.active_tags,
            )

            # Пытаемся получить из кэша
            cached = cache.get_processed(p_proc)
            if cached and "processed_text" in cached:
                processed_text = cached["processed_text"]
                meta = cached.get("meta", {}) or {}
            else:
                # Обрабатываем файл адаптером
                processed_text, meta = adapter.process(lightweight_ctx)
                
                # Кэшируем результат
                cache.put_processed(p_proc, processed_text=processed_text, meta=meta)
            
            # Создаем ProcessedFile
            processed_file = ProcessedFile(
                abs_path=fp,
                rel_path=file_entry.rel_path,
                processed_text=processed_text.rstrip("\n") + "\n",
                meta=meta,
                raw_text=raw_text,
                cache_key=k_proc
            )
            
            processed_files.append(processed_file)
    
    # Сортируем для стабильного порядка
    processed_files.sort(key=lambda f: f.rel_path)
    return processed_files


def _freeze_cfg(obj) -> tuple:
    """
    Делает объект хэшируемым и детерминированным для кэширования адаптеров.
    """
    if isinstance(obj, dict):
        return tuple((k, _freeze_cfg(v)) for k, v in sorted(obj.items(), key=lambda kv: kv[0]))
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze_cfg(x) for x in obj)
    if isinstance(obj, set):
        return tuple(sorted(_freeze_cfg(x) for x in obj))
    return obj


__all__ = ["process_files"]
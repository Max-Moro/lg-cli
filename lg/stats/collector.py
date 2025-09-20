"""
Инкрементальный коллектор статистики.

Собирает метрики постепенно в процессе рендеринга шаблонов и секций,
обеспечивая корректный учет активных режимов, тегов и условных блоков.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..stats import TokenService
from ..types import FileRow, Totals, ContextBlock, ProcessedFile, RenderedSection, SectionRef, FileStats, SectionStats


class StatsCollector:
    """
    Коллектор статистики, встроенный в процесс рендеринга шаблонов.
    
    Собирает метрики инкрементально, по мере обработки шаблонов и секций.
    Обеспечивает корректный учет:
    - Активных режимов и тегов
    - Условных блоков 
    - Переопределений режимов через {% mode %} блоки
    - Кэширования токенов
    """
    
    def __init__(self, tokenizer: TokenService):
        """
        Инициализирует коллектор статистики.
        
        Args:
            tokenizer: Сервис подсчета токенов (с встроенным кешированием)
        """
        self.tokenizer = tokenizer
        self.target_name: Optional[str] = None
        
        # Статистика по файлам (ключ: rel_path)
        self.files_stats: Dict[str, FileStats] = {}
        
        # Статистика по секциям (ключ: canon_key)
        self.sections_stats: Dict[str, SectionStats] = {}

        # Карта использования секций {canon_key: count}
        self.sections_usage: Dict[str, int] = {}

        # Итоговые тексты для подсчета финальных токенов
        self.final_text: Optional[str] = None

    def set_target_name(self, target_name: str) -> None:
        """Устанавливает имя цели (контекста/секции)."""
        self.target_name = target_name
    
    def register_processed_file(
        self, 
        file: ProcessedFile, 
        section_ref: SectionRef
    ) -> None:
        """
        Регистрирует статистику обработанного файла.
        
        Args:
            file: Обработанный файл
            section_ref: Ссылка на секцию, в которой используется файл
        """
        rel_path = file.rel_path
        canon_key = section_ref.canon_key()
        
        # Подсчитываем токены с использованием кэша
        t_proc = self.tokenizer.count_text_cached(file.processed_text)
        t_raw = self.tokenizer.count_text_cached(file.raw_text)
        
        # Вычисляем статистику для файла
        saved_tokens = max(0, t_raw - t_proc)
        saved_pct = (1 - (t_proc / t_raw)) * 100.0 if t_raw else 0.0
        
        # Регистрируем или обновляем статистику файла
        if rel_path not in self.files_stats:
            self.files_stats[rel_path] = FileStats(
                path=rel_path,
                size_bytes=file.abs_path.stat().st_size if file.abs_path.exists() else 0,
                tokens_raw=t_raw,
                tokens_processed=t_proc,
                saved_tokens=saved_tokens,
                saved_pct=saved_pct,
                meta=file.meta.copy() if file.meta else {},
                sections=[canon_key]
            )
        else:
            # Файл уже учтен, добавляем секцию если её еще нет
            stats = self.files_stats[rel_path]
            if canon_key not in stats.sections:
                stats.sections.append(canon_key)

    def register_section_rendered(self, section: RenderedSection) -> None:
        """
        Регистрирует статистику отрендеренной секции.
        Подсчитывает статистику на основе содержимого секции и файлов.
        
        Args:
            section: Отрендеренная секция
        """
        canon_key = section.ref.canon_key()
        
        self.sections_usage[canon_key] = self.sections_usage.get(canon_key, 0) + 1
        
        # Подсчитываем токены отрендеренной секции с использованием кэша
        tokens_rendered = self.tokenizer.count_text_cached(section.text)
        
        # Подсчитываем общий размер файлов
        total_size_bytes = sum(
            file.abs_path.stat().st_size if file.abs_path.exists() else 0 
            for file in section.files
        )
        
        # Собираем метаданные со всех файлов
        meta_summary = {}
        for file in section.files:
            for k, v in self._extract_numeric_meta(file.meta).items():
                meta_summary[k] = meta_summary.get(k, 0) + v
        
        # Создаем статистику секции
        self.sections_stats[canon_key] = SectionStats(
            ref=section.ref,
            text=section.text,
            tokens_rendered=tokens_rendered,
            total_size_bytes=total_size_bytes,
            meta_summary=meta_summary
        )
    
    def set_final_texts(self, final_text: str) -> None:
        """
        Устанавливает итоговые тексты для подсчета финальных токенов.
        
        Args:
            final_text: Полностью отрендеренный документ (с шаблонным "клеем")
        """
        self.final_text = final_text

    def compute_final_stats(self) -> Tuple[List[FileRow], Totals, ContextBlock]:
        """
        Вычисляет итоговую статистику на основе собранных данных.
        
        Возвращает структуру, совместимую со старым API:
        - список статистики по файлам
        - общую статистику
        - статистику контекста
        
        Returns:
            Кортеж (files_rows, totals, context_block)
            
        Raises:
            ValueError: Если итоговые тексты не установлены
        """
        if self.final_text is None:
            raise ValueError("Final texts not set. Call set_final_texts() before computing stats.")

        # Подсчитываем токены с использованием кэша
        final_tokens = self.tokenizer.count_text_cached(self.final_text)
        sections_only_tokens = sum(s.tokens_rendered for s in self.sections_stats.values())

        # Вычисляем общие суммы
        total_raw = sum(f.tokens_raw for f in self.files_stats.values())
        total_proc = sum(f.tokens_processed for f in self.files_stats.values())
        total_size = sum(f.size_bytes for f in self.files_stats.values())
        
        # Собираем общую метасводку
        meta_summary = {}
        for file_stats in self.files_stats.values():
            for k, v in self._extract_numeric_meta(file_stats.meta).items():
                meta_summary[k] = meta_summary.get(k, 0) + v
        
        # Получаем информацию о модели для подсчета shares
        model_info = self.tokenizer.model_info
        
        # Преобразуем статистику файлов в формат API
        files_rows = []
        for file_stats in sorted(self.files_stats.values(), key=lambda x: x.path):
            prompt_share = (file_stats.tokens_processed / total_proc * 100.0) if total_proc else 0.0
            ctx_share = (file_stats.tokens_processed / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0
            
            files_rows.append(FileRow(
                path=file_stats.path,
                sizeBytes=file_stats.size_bytes,
                tokensRaw=file_stats.tokens_raw,
                tokensProcessed=file_stats.tokens_processed,
                savedTokens=file_stats.saved_tokens,
                savedPct=file_stats.saved_pct,
                promptShare=prompt_share,
                ctxShare=ctx_share,
                meta=file_stats.meta or {}
            ))
        
        # Создаем итоговую статистику
        totals = Totals(
            sizeBytes=total_size,
            tokensProcessed=total_proc,
            tokensRaw=total_raw,
            savedTokens=max(0, total_raw - total_proc),
            savedPct=(1 - (total_proc / total_raw)) * 100.0 if total_raw else 0.0,
            ctxShare=(total_proc / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0,
            renderedTokens=sections_only_tokens,
            renderedOverheadTokens=max(0, (sections_only_tokens or 0) - total_proc),
            metaSummary=meta_summary
        )
        
        # Создаем статистику контекста
        template_overhead_tokens = max(0, (final_tokens or 0) - (sections_only_tokens or 0))
        template_overhead_pct = 0.0
        if final_tokens and final_tokens > 0:
            template_overhead_pct = (template_overhead_tokens / final_tokens * 100.0)
        
        ctx_block = ContextBlock(
            templateName=self.target_name or "unknown",
            sectionsUsed=self.sections_usage.copy(),
            finalRenderedTokens=final_tokens,
            templateOnlyTokens=template_overhead_tokens,
            templateOverheadPct=template_overhead_pct,
            finalCtxShare=(final_tokens / model_info.ctx_limit * 100.0) if model_info.ctx_limit and final_tokens else 0.0
        )
        
        return files_rows, totals, ctx_block

    # -------------------- Внутренние методы -------------------- #
    
    def _extract_numeric_meta(self, meta: Dict) -> Dict[str, int]:
        """
        Извлекает числовые метаданные для агрегации.
        
        Args:
            meta: Словарь метаданных
            
        Returns:
            Словарь с числовыми значениями
        """
        out: Dict[str, int] = {}
        for k, v in (meta or {}).items():
            try:
                if isinstance(v, bool):
                    v = int(v)
                if isinstance(v, (int, float)):
                    out[k] = int(v)
            except Exception:
                pass
        return out
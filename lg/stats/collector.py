"""
Incremental statistics collector.

Collects metrics gradually during the rendering of templates and sections,
ensuring correct accounting of active modes, tags, and conditional blocks.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .tokenizer import TokenService
from ..addressing.types import ResolvedSection
from ..types import FileRow, Totals, ContextBlock, ProcessedFile, RenderedSection, FileStats, SectionStats


class StatsCollector:
    """
    Statistics collector embedded in the template rendering process.

    Collects metrics incrementally as templates and sections are processed.
    Ensures correct accounting of:
    - Active modes and tags
    - Conditional blocks
    - Mode overrides via {% mode %} blocks
    - Token caching
    """
    
    def __init__(self, ctx_limit: int, tokenizer: TokenService):
        """
        Initialize the statistics collector.

        Args:
            tokenizer: Token counting service (with built-in caching)
            ctx_limit: Context window size in tokens
        """
        self.ctx_limit = ctx_limit
        self.tokenizer = tokenizer
        self.target_name: Optional[str] = None

        # Statistics by file (key: rel_path)
        self.files_stats: Dict[str, FileStats] = {}

        # Statistics by section (key: canon_key)
        self.sections_stats: Dict[str, SectionStats] = {}

        # Map of section usage {canon_key: count}
        self.sections_usage: Dict[str, int] = {}

        # Final text for counting final tokens
        self.final_text: Optional[str] = None

    def set_target_name(self, target_name: str) -> None:
        """Set the target name (context/section)."""
        self.target_name = target_name
    
    def register_processed_file(
        self,
        file: ProcessedFile,
        resolved: ResolvedSection
    ) -> None:
        """
        Register statistics for a processed file.

        Args:
            file: Processed file
            resolved: Resolved section where the file is used
        """
        rel_path = file.rel_path
        canon_key = resolved.canon_key()

        # Count tokens using cache
        t_proc = self.tokenizer.count_text_cached(file.processed_text)
        t_raw = self.tokenizer.count_text_cached(file.raw_text)

        # Calculate file statistics
        # Can be positive (optimization) or negative (additional rendering)
        saved_tokens = t_raw - t_proc
        saved_pct = (1 - (t_proc / t_raw)) * 100.0 if t_raw else 0.0

        # Register or update file statistics
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
            # File already registered, add section if not present
            stats = self.files_stats[rel_path]
            if canon_key not in stats.sections:
                stats.sections.append(canon_key)

    def register_section_rendered(self, section: RenderedSection) -> None:
        """
        Register statistics for a rendered section.
        Calculates statistics based on section content and files.

        Args:
            section: Rendered section
        """
        canon_key = section.resolved.canon_key()
        self.sections_usage[canon_key] = self.sections_usage.get(canon_key, 0) + 1

        # Count rendered section tokens using cache
        tokens_rendered = self.tokenizer.count_text_cached(section.text)

        # Calculate total file size
        total_size_bytes = sum(
            file.abs_path.stat().st_size if file.abs_path.exists() else 0
            for file in section.files
        )

        # Collect metadata from all files
        meta_summary = {}
        for file in section.files:
            for k, v in self._extract_numeric_meta(file.meta).items():
                meta_summary[k] = meta_summary.get(k, 0) + v

        # Create section statistics
        self.sections_stats[canon_key] = SectionStats(
            resolved=section.resolved,
            text=section.text,
            tokens_rendered=tokens_rendered,
            total_size_bytes=total_size_bytes,
            meta_summary=meta_summary
        )
    
    def set_final_texts(self, final_text: str) -> None:
        """
        Set final text for counting final tokens.

        Args:
            final_text: Fully rendered document (with template "glue")
        """
        self.final_text = final_text

    def compute_final_stats(self) -> Tuple[List[FileRow], Totals, ContextBlock]:
        """
        Calculate final statistics based on collected data.

        Returns a structure compatible with the legacy API:
        - list of file statistics
        - overall statistics
        - context statistics

        Returns:
            Tuple (files_rows, totals, context_block)

        Raises:
            ValueError: If final texts are not set
        """
        if self.final_text is None:
            raise ValueError("Final texts not set. Call set_final_texts() before computing stats.")

        # Count tokens using cache
        final_tokens = self.tokenizer.count_text_cached(self.final_text)
        sections_only_tokens = sum(s.tokens_rendered for s in self.sections_stats.values())

        # Calculate totals
        total_raw = sum(f.tokens_raw for f in self.files_stats.values())
        total_proc = sum(f.tokens_processed for f in self.files_stats.values())
        total_size = sum(f.size_bytes for f in self.files_stats.values())

        # Collect overall metadata summary
        meta_summary = {}
        for file_stats in self.files_stats.values():
            for k, v in self._extract_numeric_meta(file_stats.meta).items():
                meta_summary[k] = meta_summary.get(k, 0) + v

        # Convert file statistics to API format
        files_rows = []
        for file_stats in sorted(self.files_stats.values(), key=lambda x: x.path):
            prompt_share = (file_stats.tokens_processed / total_proc * 100.0) if total_proc else 0.0
            ctx_share = (file_stats.tokens_processed / self.ctx_limit * 100.0) if self.ctx_limit else 0.0

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

        # Create overall statistics
        # savedTokens can be negative if adapters added more content (tags, comments)
        totals = Totals(
            sizeBytes=total_size,
            tokensProcessed=total_proc,
            tokensRaw=total_raw,
            savedTokens=total_raw - total_proc,
            savedPct=(1 - (total_proc / total_raw)) * 100.0 if total_raw else 0.0,
            ctxShare=(total_proc / self.ctx_limit * 100.0) if self.ctx_limit else 0.0,
            renderedTokens=sections_only_tokens,
            renderedOverheadTokens=(sections_only_tokens or 0) - total_proc,
            metaSummary=meta_summary
        )

        # Create context statistics
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
            finalCtxShare=(final_tokens / self.ctx_limit * 100.0) if self.ctx_limit and final_tokens else 0.0
        )

        return files_rows, totals, ctx_block

    # -------------------- Internal methods -------------------- #

    def _extract_numeric_meta(self, meta: Dict) -> Dict[str, int]:
        """
        Extract numeric metadata for aggregation.

        Args:
            meta: Dictionary of metadata

        Returns:
            Dictionary with numeric values
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
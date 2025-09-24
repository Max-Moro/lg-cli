from __future__ import annotations

import re


class MarkdownNormalizer:
    """
    Нормализатор Markdown с поддержкой различных сценариев:
    - Обычная нормализация с сдвигом заголовков
    - Специальная обработка плейсхолдеров внутри заголовков
    - Удаление H1 заголовков при необходимости
    - Ограничение максимального уровня заголовков до H6
    """
    
    def __init__(self):
        self.fence_pattern = re.compile(r"^```")
        self.heading_pattern = re.compile(r"^(#+)\s")
        self.atx_h1_pattern = re.compile(r"^#\s")
        self.setext_underline_pattern = re.compile(r"^={2,}\s*$")
        self.setext_h2_underline_pattern = re.compile(r"^-{2,}$")
        self.atx_heading_with_text_pattern = re.compile(r"^#+\s+(.+)$")
    
    def normalize(
        self,
        text: str, *,
        max_heading_level: int | None,
        strip_single_h1: bool,
        group_size: int,
        mixed: bool,
        placeholder_inside_heading: bool = False
    ) -> tuple[str, dict]:
        """
        Основной метод нормализации Markdown.
        
        Args:
            text: Исходный Markdown текст
            max_heading_level: Максимальный уровень заголовков (или None)
            strip_single_h1: Удалять ли верхний H1
            group_size: Размер группы файлов
            mixed: Контент в секции не только Markdown (смешан с другими языками)
            placeholder_inside_heading: Плейсхолдер внутри заголовка
            
        Returns:
            Кортеж (нормализованный_текст, метаданные)
        """
        meta = {"md.removed_h1": 0, "md.shifted": False}
        
        # Специальная обработка для плейсхолдеров внутри заголовков
        if placeholder_inside_heading:
            return self._process_placeholder_heading(text, meta, max_heading_level)
        
        # Обычная обработка
        return self._process_normal(
            text, meta, max_heading_level, strip_single_h1, 
            group_size, mixed
        )
    
    def _process_placeholder_heading(
        self, 
        text: str, 
        meta: dict, 
        max_heading_level: int | None
    ) -> tuple[str, dict]:
        """
        Обработка Markdown для плейсхолдеров внутри заголовков.
        Извлекает текст заголовка и включает остальной контент со сдвигом.
        """
        lines = text.strip().splitlines()
        
        if not lines:
            return "", meta
        
        # Извлекаем заголовок и остальной контент
        heading_info = self._extract_heading_info(lines)
        
        if heading_info.text:
            meta["md.removed_h1"] = 1
        
        # Формируем результат
        result_parts = [heading_info.text]
        
        if heading_info.remaining_lines:
            # Убираем пустые строки в начале
            content_lines = self._skip_empty_lines(heading_info.remaining_lines)
            
            if content_lines and max_heading_level is not None:
                # Применяем сдвиг заголовков к контенту
                shifted_lines = self._shift_headings(content_lines, max_heading_level + 1)
                result_parts.append("")  # Разделитель
                result_parts.extend(shifted_lines)
            elif content_lines:
                result_parts.append("")  # Разделитель
                result_parts.extend(content_lines)
        
        return "\n".join(result_parts), meta
    
    def _process_normal(
        self,
        text: str,
        meta: dict,
        max_heading_level: int | None,
        strip_single_h1: bool,
        group_size: int,
        mixed: bool
    ) -> tuple[str, dict]:
        """
        Обычная обработка Markdown с нормализацией заголовков.
        """
        lines = text.splitlines()
        
        # Удаляем H1 если необходимо
        if strip_single_h1:
            lines, removed_h1 = self._strip_h1_if_needed(lines, group_size)
            if removed_h1:
                meta["md.removed_h1"] = 1
        
        # Если нет ограничений на уровень заголовков, возвращаем как есть
        if max_heading_level is None or mixed:
            return "\n".join(lines), meta
        
        # Применяем нормализацию заголовков
        return self._normalize_heading_levels(lines, meta, max_heading_level)
    
    def _extract_heading_info(self, lines: list[str]) -> 'HeadingInfo':
        """
        Извлекает информацию о заголовке из начала документа.
        
        Returns:
            HeadingInfo с текстом заголовка и оставшимися строками
        """
        if not lines:
            return HeadingInfo("", [])
        
        first_line = lines[0].strip()
        
        # ATX заголовок: "# Title" -> "Title"
        atx_match = self.atx_heading_with_text_pattern.match(first_line)
        if atx_match:
            return HeadingInfo(
                text=atx_match.group(1).strip(),
                remaining_lines=lines[1:]
            )
        
        # Setext заголовки
        if len(lines) >= 2:
            second_line = lines[1].strip()
            
            # H1: "Title" + "====" -> "Title"
            if first_line and self.setext_underline_pattern.match(second_line):
                return HeadingInfo(
                    text=first_line.strip(),
                    remaining_lines=lines[2:]
                )
            
            # H2: "Title" + "----" -> "Title"
            if first_line and self.setext_h2_underline_pattern.match(second_line):
                return HeadingInfo(
                    text=first_line.strip(),
                    remaining_lines=lines[2:]
                )
        
        # Заголовок не найден - используем первую строку
        return HeadingInfo(
            text=first_line,
            remaining_lines=lines[1:] if len(lines) > 1 else []
        )
    
    def _strip_h1_if_needed(self, lines: list[str], group_size: int) -> tuple[list[str], bool]:
        """
        Удаляет верхний H1 заголовок если файл одиночный в группе.
        
        Returns:
            Кортеж (новые_строки, удален_ли_h1)
        """
        if group_size != 1 or not lines:
            return lines, False
        
        # ATX H1: "# Title"
        if self.atx_h1_pattern.match(lines[0]):
            return lines[1:], True
        
        # Setext H1: "Title" + "===="
        if (len(lines) >= 2 and 
            lines[0].strip() and 
            self.setext_underline_pattern.match(lines[1])):
            return lines[2:], True
        
        return lines, False
    
    def _normalize_heading_levels(
        self, 
        lines: list[str], 
        meta: dict, 
        max_heading_level: int
    ) -> tuple[str, dict]:
        """
        Нормализует уровни заголовков с учетом fenced блоков.
        """
        # Находим минимальный уровень заголовков вне fenced блоков
        min_level = self._find_min_heading_level(lines)
        
        if min_level is None:
            return "\n".join(lines), meta
        
        # Вычисляем сдвиг
        shift = max_heading_level - min_level
        meta["md.shifted"] = bool(shift)
        
        if shift == 0:
            return "\n".join(lines), meta
        
        # Применяем сдвиг
        normalized_lines = self._apply_heading_shift(lines, shift)
        return "\n".join(normalized_lines), meta
    
    def _find_min_heading_level(self, lines: list[str]) -> int | None:
        """
        Находит минимальный уровень заголовков вне fenced блоков.
        """
        min_level = None
        in_fence = False
        
        for line in lines:
            if self.fence_pattern.match(line):
                in_fence = not in_fence
                continue
            
            if in_fence:
                continue
            
            match = self.heading_pattern.match(line)
            if match:
                level = len(match.group(1))
                min_level = level if min_level is None else min(min_level, level)
        
        return min_level
    
    def _apply_heading_shift(self, lines: list[str], shift: int) -> list[str]:
        """
        Применяет сдвиг уровней заголовков с учетом fenced блоков.
        """
        result = []
        in_fence = False
        
        for line in lines:
            if self.fence_pattern.match(line):
                in_fence = not in_fence
                result.append(line)
                continue
            
            if in_fence:
                result.append(line)
                continue
            
            match = self.heading_pattern.match(line)
            if match:
                new_level = len(match.group(1)) + shift
                # Ограничиваем максимальный уровень до H6
                new_level = min(new_level, 6)
                new_hashes = "#" * new_level
                result.append(f"{new_hashes} {line[match.end():]}")
            else:
                result.append(line)
        
        return result
    
    def _shift_headings(self, lines: list[str], target_min_level: int) -> list[str]:
        """
        Сдвигает заголовки так, чтобы минимальный уровень стал target_min_level.
        """
        if not lines:
            return lines
        
        # Находим минимальный уровень
        min_level = None
        for line in lines:
            match = self.heading_pattern.match(line)
            if match:
                level = len(match.group(1))
                min_level = level if min_level is None else min(min_level, level)
        
        if min_level is None:
            return lines
        
        shift = target_min_level - min_level
        if shift == 0:
            return lines
        
        return self._apply_simple_heading_shift(lines, shift)
    
    def _apply_simple_heading_shift(self, lines: list[str], shift: int) -> list[str]:
        """
        Применяет простой сдвиг заголовков без учета fenced блоков.
        """
        result = []
        
        for line in lines:
            match = self.heading_pattern.match(line)
            if match:
                new_level = len(match.group(1)) + shift
                # Ограничиваем максимальный уровень до H6
                new_level = min(new_level, 6)
                new_hashes = "#" * new_level
                result.append(f"{new_hashes} {line[match.end():]}")
            else:
                result.append(line)
        
        return result
    
    def _skip_empty_lines(self, lines: list[str]) -> list[str]:
        """
        Пропускает пустые строки в начале списка.
        """
        while lines and not lines[0].strip():
            lines = lines[1:]
        return lines


class HeadingInfo:
    """
    Информация о заголовке, извлеченная из документа.
    """
    
    def __init__(self, text: str, remaining_lines: list[str]):
        self.text = text
        self.remaining_lines = remaining_lines


def normalize_markdown(
    text: str, *,
    max_heading_level: int | None,
    strip_single_h1: bool,
    group_size: int,
    mixed: bool,
    placeholder_inside_heading: bool = False
) -> tuple[str, dict]:
    """
    Публичное API для нормализации Markdown текста перед вставкой в шаблоны
    """
    normalizer = MarkdownNormalizer()
    return normalizer.normalize(
        text,
        max_heading_level=max_heading_level,
        strip_single_h1=strip_single_h1,
        group_size=group_size,
        mixed=mixed,
        placeholder_inside_heading=placeholder_inside_heading
    )

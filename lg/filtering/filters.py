"""
Движок фильтрации путей файловой системы.

Реализует древовидную систему фильтрации с поддержкой:
- Режимов allow/block (default-deny/default-allow)
- Иерархических правил с переопределениями
- Path-based синтаксиса для компактного описания правил
- Раннего отсечения директорий (pruning)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Optional

import pathspec

from .model import FilterNode


# ============================================================================
# Вспомогательные структуры
# ============================================================================

@dataclass(frozen=True)
class PathMatch:
    """Результат проверки пути на соответствие правилам."""
    matched: bool
    reason: str  # Для отладки: почему принято такое решение


@dataclass(frozen=True)
class CompiledPatterns:
    """Скомпилированные паттерны для быстрой проверки."""
    allow_spec: Optional[pathspec.PathSpec]
    block_spec: Optional[pathspec.PathSpec]
    allow_raw: List[str]  # Сырые паттерны для эвристик
    block_raw: List[str]

    @classmethod
    def compile(cls, allow: List[str], block: List[str]) -> CompiledPatterns:
        """
        Компилирует списки паттернов в PathSpec объекты.

        Все паттерны приводятся к lowercase для case-insensitive сравнения.
        """
        allow_lower = [pat.lower() for pat in allow]
        block_lower = [pat.lower() for pat in block]

        return cls(
            allow_spec=pathspec.PathSpec.from_lines("gitwildmatch", allow_lower) if allow_lower else None,
            block_spec=pathspec.PathSpec.from_lines("gitwildmatch", block_lower) if block_lower else None,
            allow_raw=allow_lower,
            block_raw=block_lower
        )


# ============================================================================
# Компилированный узел фильтрации
# ============================================================================

class CompiledFilterNode:
    """
    Скомпилированный узел фильтрации с готовыми PathSpec объектами.

    Представляет узел дерева фильтров после разворачивания path-based ключей
    и компиляции паттернов для эффективной проверки.
    """

    __slots__ = ("mode", "patterns", "children")

    def __init__(self, mode: str, patterns: CompiledPatterns, children: Dict[str, CompiledFilterNode]):
        self.mode = mode
        self.patterns = patterns
        self.children = children

    @classmethod
    def from_filter_node(cls, node: FilterNode) -> CompiledFilterNode:
        """
        Компилирует FilterNode в эффективное представление.

        Разворачивает path-based ключи в полную иерархию и компилирует
        все паттерны в PathSpec объекты.
        """
        # Сначала разворачиваем path-based ключи
        expanded_node = PathBasedExpander.expand(node)

        # Компилируем паттерны
        patterns = CompiledPatterns.compile(
            expanded_node.allow,
            expanded_node.block
        )

        # Рекурсивно компилируем дочерние узлы
        children = {
            name.lower(): cls.from_filter_node(child)
            for name, child in expanded_node.children.items()
        }

        return cls(expanded_node.mode, patterns, children)

    def check_block(self, subpath: str) -> bool:
        """Проверяет, блокируется ли путь."""
        if self.patterns.block_spec:
            return self.patterns.block_spec.match_file(subpath)
        return False

    def check_allow(self, subpath: str) -> bool:
        """Проверяет, явно разрешен ли путь."""
        if self.patterns.allow_spec:
            return self.patterns.allow_spec.match_file(subpath)
        return False

    def get_child(self, name: str) -> Optional[CompiledFilterNode]:
        """Получает дочерний узел по имени (case-insensitive)."""
        return self.children.get(name.lower())


# ============================================================================
# Разворачивание path-based иерархий
# ============================================================================

class PathBasedExpander:
    """
    Разворачивает path-based ключи в полную иерархию узлов фильтрации.

    Преобразует компактный синтаксис типа:
        children:
          "main/kotlin": {...}

    В полную иерархию:
        children:
          main:
            mode: allow
            allow: ["/kotlin/"]
            children:
              kotlin: {...}
    """

    @staticmethod
    def expand(node: FilterNode) -> FilterNode:
        """
        Разворачивает path-based ключи в узле и его детях.

        Args:
            node: Исходный узел для разворачивания

        Returns:
            Узел с развернутыми детьми

        Raises:
            RuntimeError: При обнаружении конфликтов между path-based и явными узлами
        """
        if not node.children:
            return node

        # Разделяем ключи на простые и path-based
        simple_children: Dict[str, FilterNode] = {}
        path_children: Dict[str, FilterNode] = {}

        for key, child in node.children.items():
            normalized = key.strip("/").lower()
            if "/" in normalized:
                path_children[normalized] = child
            else:
                simple_children[normalized] = child

        # Если нет path-based ключей, просто рекурсивно обрабатываем детей
        if not path_children:
            expanded_children = {
                name: PathBasedExpander.expand(child)
                for name, child in simple_children.items()
            }
            return FilterNode(
                mode=node.mode,
                allow=node.allow,
                block=node.block,
                children=expanded_children,
                conditional_filters=node.conditional_filters
            )

        # Проверяем конфликты
        PathBasedExpander._validate_no_conflicts(simple_children, path_children)

        # Строим развернутую иерархию
        expanded_children = dict(simple_children)

        for path, target_node in sorted(path_children.items()):
            PathBasedExpander._insert_path(expanded_children, path, target_node)

        # Рекурсивно обрабатываем всех детей
        final_children = {
            name: PathBasedExpander.expand(child)
            for name, child in expanded_children.items()
        }

        return FilterNode(
            mode=node.mode,
            allow=node.allow,
            block=node.block,
            children=final_children,
            conditional_filters=node.conditional_filters
        )

    @staticmethod
    def _validate_no_conflicts(
        simple_children: Dict[str, FilterNode],
        path_children: Dict[str, FilterNode]
    ) -> None:
        """
        Проверяет отсутствие конфликтов между простыми и path-based ключами.

        Конфликт возникает, если path-based ключ пересекается с явно
        определённой иерархией в простых детях или других path-based ключах.

        Допускается расширение path-based ключа другим path-based ключом,
        если нет конфликтующих явных определений дочерних узлов.
        """
        for path_key in path_children.keys():
            parts = path_key.split("/")

            # Проверяем каждый префикс пути
            for i in range(1, len(parts)):
                prefix = "/".join(parts[:i])
                suffix = "/".join(parts[i:])

                # Конфликт с простым ключом
                if prefix in simple_children:
                    if PathBasedExpander._has_child_prefix(simple_children[prefix], suffix):
                        raise RuntimeError(
                            f"Filter path conflict: '{path_key}' conflicts with "
                            f"explicit definition under '{prefix}'"
                        )

                # Конфликт с другим path-based ключом
                if prefix in path_children:
                    prefix_node = path_children[prefix]
                    # Если префиксный узел имеет детей, проверяем конфликт с суффиксом
                    # Пример: "src/main" с детьми "resources", и "src/main/kotlin/..." - OK
                    #         "src/main" с детьми "kotlin", и "src/main/kotlin/..." - КОНФЛИКТ
                    if PathBasedExpander._has_child_prefix(prefix_node, suffix):
                        raise RuntimeError(
                            f"Filter path conflict: '{path_key}' conflicts with "
                            f"explicit definition under '{prefix}'"
                        )

    @staticmethod
    def _has_child_prefix(node: FilterNode, path: str) -> bool:
        """Проверяет наличие хотя бы префикса пути в детях узла."""
        if not path:
            return False

        first_segment = path.split("/")[0]
        return first_segment in node.children

    @staticmethod
    def _extract_inherited_rules(parent_node: Optional[FilterNode], child_name: str) -> List[str]:
        """
        Извлекает правила из родительского узла, которые относятся к дочернему узлу.

        Если родительский узел имеет allow-правила типа "/child_name/subpath",
        извлекаем "/subpath" для наследования дочерним узлом.

        Args:
            parent_node: Родительский узел (или None)
            child_name: Имя дочернего узла

        Returns:
            Список унаследованных правил (пути относительно дочернего узла)
        """
        if not parent_node or not parent_node.allow:
            return []

        inherited = []
        prefix = f"/{child_name}/"

        for rule in parent_node.allow:
            if rule.startswith(prefix):
                # Убираем префикс и добавляем в наследуемые правила
                inherited_rule = rule[len(prefix):]
                # Нормализуем: добавляем "/" в начало если его нет
                if inherited_rule and not inherited_rule.startswith("/"):
                    inherited_rule = "/" + inherited_rule
                if inherited_rule:  # Пропускаем пустые правила
                    inherited.append(inherited_rule)

        return inherited

    @staticmethod
    def _insert_path(
        children_dict: Dict[str, FilterNode],
        path: str,
        target_node: FilterNode
    ) -> None:
        """
        Вставляет path-based узел в иерархию, создавая промежуточные узлы.

        Промежуточные узлы создаются с mode="allow" и allow=["/{next_segment}/"] +
        унаследованные правила из родительского узла (если есть).

        Наследование правил: если родительский узел имеет allow=["/services/generation/..."],
        и мы создаём промежуточный узел "services", то он получит allow=["/ai/", "/generation/..."].
        """
        parts = path.split("/")

        # Проходим до предпоследнего сегмента
        current_dict = children_dict
        parent_node: Optional[FilterNode] = None

        for idx, part in enumerate(parts[:-1]):
            next_segment = parts[idx + 1]

            if part not in current_dict:
                # Извлекаем унаследованные правила от родителя
                inherited_rules = PathBasedExpander._extract_inherited_rules(parent_node, part)

                # Создаем промежуточный узел с унаследованными правилами
                current_dict[part] = FilterNode(
                    mode="allow",
                    allow=[f"/{next_segment}/"] + inherited_rules,
                    block=[],
                    children={},
                    conditional_filters=[]
                )
            else:
                # Узел существует - добавляем новый сегмент в allow
                existing = current_dict[part]
                new_pattern = f"/{next_segment}/"
                if new_pattern not in existing.allow:
                    existing.allow.append(new_pattern)

            # Запоминаем текущий узел как родительский для следующей итерации
            parent_node = current_dict[part]
            current_dict = current_dict[part].children

        # Вставляем целевой узел
        current_dict[parts[-1]] = target_node


# ============================================================================
# Цепочка узлов для проверки
# ============================================================================

@dataclass(frozen=True)
class NodeInChain:
    """Узел в цепочке проверки с относительным подпутем."""
    node: CompiledFilterNode
    subpath: str  # Путь относительно этого узла


class NodeChainBuilder:
    """
    Строит цепочку узлов от корня до самого глубокого узла,
    соответствующего сегментам пути.
    """

    @staticmethod
    def build(root: CompiledFilterNode, path: str) -> List[NodeInChain]:
        """
        Строит цепочку узлов для проверки пути.

        Проходит по сегментам пути (кроме последнего, который может быть файлом)
        и собирает все узлы, для которых нужно проверить правила.

        Args:
            root: Корневой узел фильтрации
            path: Нормализованный путь (lowercase, POSIX)

        Returns:
            Список узлов с соответствующими подпутями для проверки
        """
        norm = path.lower().strip("/")
        parts = PurePosixPath(norm).parts

        chain: List[NodeInChain] = [NodeInChain(root, norm or "")]

        current_node = root

        # Проходим по всем сегментам кроме последнего
        for idx, part in enumerate(parts[:-1]):
            child = current_node.get_child(part)
            if child is None:
                break

            current_node = child
            subpath = "/".join(parts[idx + 1:]) or "."
            chain.append(NodeInChain(current_node, subpath))

        return chain


# ============================================================================
# Оценщик путей
# ============================================================================

class PathEvaluator:
    """
    Оценивает, следует ли включать путь в выборку.

    Реализует сложную логику фильтрации с учетом:
    - Приоритета block над allow
    - Жесткой семантики mode=allow (default-deny)
    - Наследования правил по цепочке узлов
    """

    @staticmethod
    def evaluate_include(chain: List[NodeInChain]) -> bool:
        """
        Определяет, следует ли включить файл по пути.

        Алгоритм:
        1. Проходим по цепочке узлов от корня к листу
        2. На каждом уровне:
           - block всегда побеждает (немедленный отказ)
           - Для mode=allow: ДОЛЖНО совпасть с локальным allow, иначе отказ
           - Для mode=block: локальный allow даёт временное разрешение
        3. Если решение не принято - fallback по mode самого глубокого узла

        Args:
            chain: Цепочка узлов с подпутями

        Returns:
            True если путь разрешен, False иначе
        """
        if not chain:
            return False

        decision: Optional[bool] = None
        deepest_node = chain[-1].node

        for item in chain:
            node = item.node
            subpath = item.subpath

            # 1. Block всегда побеждает
            if node.check_block(subpath):
                return False

            # 2. Жесткая семантика для mode=allow
            if node.mode == "allow":
                if not node.check_allow(subpath):
                    return False
                # Попали под локальный allow - продолжаем проверку
                decision = True
                continue

            # 3. mode=block: default-allow, но локальный allow усиливает
            if node.check_allow(subpath):
                decision = True

        # Fallback по mode самого глубокого узла
        if decision is not None:
            return decision

        return deepest_node.mode == "block"


class DirectoryPruner:
    """
    Определяет, следует ли спускаться в поддерево директории.

    Используется для раннего отсечения директорий при обходе ФС,
    чтобы не тратить время на сканирование заведомо ненужных веток.
    """

    @staticmethod
    def may_descend(chain: List[NodeInChain]) -> bool:
        """
        Проверяет, имеет ли смысл спускаться в директорию.

        Консервативная проверка: False = точно бесполезно, True = возможно полезно.

        Args:
            chain: Цепочка узлов для директории

        Returns:
            True если спуск потенциально полезен
        """
        if not chain:
            return True

        decision: Optional[bool] = None
        deepest_node = chain[-1].node

        for item in chain:
            node = item.node
            subpath = item.subpath

            # 1. Блокирующее правило - спуск бесполезен
            if DirectoryPruner._check_dir_blocked(node, subpath):
                return False

            # 2. Режим allow - проверяем возможность совпадений в глубине
            if node.mode == "allow":
                if not node.patterns.allow_spec:
                    return False

                if DirectoryPruner._may_match_in_subtree(node, subpath):
                    decision = True
                else:
                    return False
            else:
                # 3. Режим block - спуск потенциально полезен
                if DirectoryPruner._check_dir_allowed(node, subpath):
                    decision = True

        if decision is not None:
            return decision

        # Fallback: в block-режиме можно спускаться
        return deepest_node.mode == "block"

    @staticmethod
    def _check_dir_blocked(node: CompiledFilterNode, subpath: str) -> bool:
        """Проверяет, блокируется ли директория."""
        if not node.patterns.block_spec:
            return False

        return (
            node.patterns.block_spec.match_file(subpath) or
            node.patterns.block_spec.match_file(subpath + "/")
        )

    @staticmethod
    def _check_dir_allowed(node: CompiledFilterNode, subpath: str) -> bool:
        """Проверяет, явно разрешена ли директория."""
        if not node.patterns.allow_spec:
            return False

        return (
            node.patterns.allow_spec.match_file(subpath) or
            node.patterns.allow_spec.match_file(subpath + "/") or
            node.patterns.allow_spec.match_file(subpath + "/x")
        )

    @staticmethod
    def _may_match_in_subtree(node: CompiledFilterNode, subpath: str) -> bool:
        """
        Быстрая эвристика: может ли что-то совпасть в поддереве.

        Проверяет сырые паттерны на предмет:
        - Basename-паттернов без '/' (матчатся везде)
        - Паттернов с '**' (матчатся в глубине)
        - Паттернов, начинающихся с текущего пути
        """
        subpath_clean = subpath.lstrip("/")

        for pat in node.patterns.allow_raw:
            # Паттерны с ** матчатся в глубине
            if "**" in pat:
                return True

            # Basename-паттерны без / матчатся везде
            if "/" not in pat:
                return True

            # Паттерны, начинающиеся с текущего пути
            if pat.startswith(subpath_clean + "/") or pat.startswith("/" + subpath_clean + "/"):
                return True

        # Консервативная проверка через PathSpec
        return (
            node.patterns.allow_spec.match_file(subpath) or
            node.patterns.allow_spec.match_file(subpath + "/") or
            node.patterns.allow_spec.match_file(subpath + "/x")
        )


# ============================================================================
# Основной движок фильтрации
# ============================================================================

class FilterEngine:
    """
    Движок фильтрации путей файловой системы.

    Предоставляет два основных метода:
    - includes(): решает, включать ли файл
    - may_descend(): решает, спускаться ли в директорию (для pruning)

    Использует скомпилированное дерево фильтров для эффективной проверки.
    """

    def __init__(self, root: FilterNode):
        """
        Инициализирует движок фильтрации.

        Args:
            root: Корневой узел дерева фильтров
        """
        self._root = CompiledFilterNode.from_filter_node(root)

    def includes(self, rel_path: str) -> bool:
        """
        Проверяет, следует ли включить файл по пути.

        Args:
            rel_path: Относительный путь файла (от корня репозитория)

        Returns:
            True если файл разрешен правилами фильтрации
        """
        chain = NodeChainBuilder.build(self._root, rel_path)
        return PathEvaluator.evaluate_include(chain)

    def may_descend(self, rel_dir: str) -> bool:
        """
        Проверяет, следует ли спускаться в директорию.

        Используется для раннего отсечения директорий при обходе ФС.
        Консервативная проверка: False = точно бесполезно, True = возможно полезно.

        Args:
            rel_dir: Относительный путь директории (от корня репозитория)

        Returns:
            True если спуск в директорию потенциально полезен
        """
        norm = rel_dir.strip("/").lower()
        if not norm:
            return True  # Корень всегда доступен

        chain = NodeChainBuilder.build(self._root, norm)
        return DirectoryPruner.may_descend(chain)


# ============================================================================
# Публичный API
# ============================================================================

__all__ = [
    "FilterEngine",
    "PathMatch",
    "CompiledFilterNode",
]

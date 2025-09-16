"""
Модели данных для системы адаптивных возможностей.
Содержит классы для режимов, тегов и их наборов с поддержкой сериализации в YAML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal


@dataclass
class Mode:
    """
    Режим - конкретная опция внутри набора режимов.
    
    Активирует определенные теги и может содержать специальные настройки.
    """
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mode":
        """Создание экземпляра из словаря (из YAML)."""
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            tags=list(data.get("tags", [])),
            options=dict(data.get("options", {})) if "options" in data else {
                k: v for k, v in data.items() 
                if k not in {"title", "description", "tags"}
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        result: Dict[str, Any] = {"title": self.title}
        if self.description:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        # Добавляем дополнительные опции напрямую
        result.update(self.options)
        return result


@dataclass
class ModeSet:
    """
    Набор режимов - группа взаимоисключающих опций.
    
    Представляет определенный аспект работы (например, "Способ работы с AI").
    """
    title: str
    modes: Dict[str, Mode] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModeSet":
        """Создание экземпляра из словаря (из YAML)."""
        modes = {}
        modes_data = data.get("modes", {})
        for mode_name, mode_data in modes_data.items():
            if isinstance(mode_data, dict):
                modes[mode_name] = Mode.from_dict(mode_data)
            else:
                # Упрощенная форма: только title
                modes[mode_name] = Mode(title=str(mode_data))
        
        return cls(
            title=str(data.get("title", "")),
            modes=modes
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        return {
            "title": self.title,
            "modes": {name: mode.to_dict() for name, mode in self.modes.items()}
        }


@dataclass
class Tag:
    """
    Тег - атомарный элемент фильтрации.
    
    Может быть активирован или деактивирован для настройки генерируемых контекстов.
    """
    title: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | str) -> "Tag":
        """Создание экземпляра из словаря или строки (из YAML)."""
        if isinstance(data, str):
            return cls(title=data)
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", ""))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        result = {"title": self.title}
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class TagSet:
    """
    Набор тегов - группа взаимосвязанных тегов.
    
    Представляет определенную категорию (например, "Языки программирования").
    """
    title: str
    tags: Dict[str, Tag] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagSet":
        """Создание экземпляра из словаря (из YAML)."""
        tags = {}
        tags_data = data.get("tags", {})
        for tag_name, tag_data in tags_data.items():
            tags[tag_name] = Tag.from_dict(tag_data)
        
        return cls(
            title=str(data.get("title", "")),
            tags=tags
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        return {
            "title": self.title,
            "tags": {name: tag.to_dict() for name, tag in self.tags.items()}
        }


@dataclass
class ModesConfig:
    """
    Полная конфигурация режимов из modes.yaml.
    """
    mode_sets: Dict[str, ModeSet] = field(default_factory=dict)
    include: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModesConfig":
        """Создание экземпляра из словаря (из YAML)."""
        mode_sets = {}
        mode_sets_data = data.get("mode-sets", {})
        for set_name, set_data in mode_sets_data.items():
            mode_sets[set_name] = ModeSet.from_dict(set_data)
        
        return cls(
            mode_sets=mode_sets,
            include=list(data.get("include", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        result = {}
        if self.mode_sets:
            result["mode-sets"] = {name: mode_set.to_dict() for name, mode_set in self.mode_sets.items()}
        if self.include:
            result["include"] = self.include
        return result


@dataclass
class TagsConfig:
    """
    Полная конфигурация тегов из tags.yaml.
    """
    tag_sets: Dict[str, TagSet] = field(default_factory=dict)
    global_tags: Dict[str, Tag] = field(default_factory=dict)
    include: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagsConfig":
        """Создание экземпляра из словаря (из YAML)."""
        # Наборы тегов
        tag_sets = {}
        tag_sets_data = data.get("tag-sets", {})
        for set_name, set_data in tag_sets_data.items():
            tag_sets[set_name] = TagSet.from_dict(set_data)
        
        # Глобальные теги (не входят в определенные наборы)
        global_tags = {}
        global_tags_data = data.get("tags", {})
        for tag_name, tag_data in global_tags_data.items():
            global_tags[tag_name] = Tag.from_dict(tag_data)
        
        return cls(
            tag_sets=tag_sets,
            global_tags=global_tags,
            include=list(data.get("include", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь для YAML."""
        result = {}
        if self.tag_sets:
            result["tag-sets"] = {name: tag_set.to_dict() for name, tag_set in self.tag_sets.items()}
        if self.global_tags:
            result["tags"] = {name: tag.to_dict() for name, tag in self.global_tags.items()}
        if self.include:
            result["include"] = self.include
        return result


# Стандартная конфигурация по умолчанию
DEFAULT_MODES_CONFIG = ModesConfig(
    mode_sets={
        "ai-interaction": ModeSet(
            title="Способ работы с AI",
            modes={
                "ask": Mode(
                    title="Спросить",
                    description="Базовый режим вопрос-ответ"
                ),
                "agent": Mode(
                    title="Агентная работа", 
                    description="Режим с инструментами",
                    tags=["agent", "tools"],
                    options={"allow_tools": True}
                )
            }
        ),
        "dev-stage": ModeSet(
            title="Стадия работы над фичей",
            modes={
                "planning": Mode(
                    title="Планирование",
                    tags=["architecture", "docs"]
                ),
                "development": Mode(
                    title="Основная разработка"
                ),
                "testing": Mode(
                    title="Написание тестов",
                    tags=["tests"]
                ),
                "review": Mode(
                    title="Кодревью",
                    tags=["review"],
                    options={"vcs_mode": "changes"}
                )
            }
        )
    }
)

DEFAULT_TAGS_CONFIG = TagsConfig(
    tag_sets={
        "language": TagSet(
            title="Языки программирования",
            tags={
                "python": Tag(title="Python"),
                "typescript": Tag(title="TypeScript"),
                "javascript": Tag(title="JavaScript")
            }
        ),
        "code-type": TagSet(
            title="Тип кода",
            tags={
                "product": Tag(title="Продуктовый код"),
                "tests": Tag(title="Тестовый код"),
                "generated": Tag(title="Сгенерированный код")
            }
        )
    },
    global_tags={
        "agent": Tag(title="Агентные возможности"),
        "review": Tag(title="Правила проведения кодревью"),
        "architecture": Tag(title="Архитектурная документация"),
        "docs": Tag(title="Документация"),
        "tests": Tag(title="Тестовый код"),
        "tools": Tag(title="Инструменты")
    }
)


@dataclass
class ModeOptions:
    """
    Типизированный контейнер для смердженных опций от всех активных режимов.
    
    Содержит все возможные опции, которые могут быть определены в режимах,
    с разумными значениями по умолчанию.
    """
    # VCS опции
    vcs_mode: Literal["all", "changes"] = "all"
    
    # Инструментальные возможности
    allow_tools: bool = False  # разрешение использования инструментов в агентном режиме
    
    # Дополнительные опции можно добавлять по мере необходимости

    @classmethod
    def merge_from_modes(cls, modes_config: ModesConfig, active_modes: Dict[str, str]) -> "ModeOptions":
        """
        Создает MergedModeOptions путем мержинга опций из всех активных режимов.
        
        Args:
            modes_config: Конфигурация всех доступных режимов
            active_modes: Словарь активных режимов {modeset_name: mode_name}
            
        Returns:
            MergedModeOptions с объединенными настройками
        """
        result = cls()
        
        # Проходим по всем активным режимам и собираем их опции
        for modeset_name, mode_name in active_modes.items():
            modeset = modes_config.mode_sets.get(modeset_name)
            if not modeset:
                continue
                
            mode = modeset.modes.get(mode_name)
            if not mode or not mode.options:
                continue
            
            # Мержим опции в типизированный датакласс
            for option_key, option_value in mode.options.items():
                if option_key == "vcs_mode" and isinstance(option_value, str):
                    result.vcs_mode = option_value
                elif option_key == "allow_tools" and isinstance(option_value, bool):
                    result.allow_tools = option_value
                # Здесь можно добавить обработку других опций
        
        return result
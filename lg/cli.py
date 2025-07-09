from __future__ import annotations
import sys
import argparse
import logging
from pathlib import Path

from lg.config import (
    load_config,
    list_sections,
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_FILE,
    DEFAULT_SECTION_NAME,
)
from lg.core.generator import generate_listing
from lg.context import generate_context


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="listing-generator",
        description="Generate source listings or context-prompts based on lg-cfg/",
    )
    p.add_argument(
        "-s", "--section",
        default=DEFAULT_SECTION_NAME,
        help=(
            f"Section name from {DEFAULT_CONFIG_DIR}/{DEFAULT_CONFIG_FILE} "
            f"(default: {DEFAULT_SECTION_NAME})"
        ),
    )
    p.add_argument(
        "--list-sections",
        action="store_true",
        help="List available sections in the config and exit",
    )
    p.add_argument(
        "--context",
        metavar="NAME",
        help="Generate a prompt from template lg-cfg/contexts/NAME.tmpl.md",
    )
    p.add_argument(
        "--mode",
        choices=("all", "changes"),
        default="all",
        help="all = entire project; changes = only modified git files",
    )
    p.add_argument(
        "--list-included",
        action="store_true",
        help="If set, only print included paths (debug mode)",
    )
    p.add_argument(
        "-v", "--verbose",
        action="count", default=0,
        help="Increase log verbosity (repeatable)",
    )
    p.add_argument(
        "--code-fence",
        action="store_true",
        help="Wrap each file listing in fenced markdown block (```lang)",
    )
    p.add_argument(
        "--max-heading-level",
        type=int,
        default=None,
        help="Max heading level for Markdown normalization (overrides config)",
    )
    return p


def main() -> None:
    ns = _build_parser().parse_args()

    # 1. Определяем корень (cwd) и путь до конфига
    root = Path.cwd()
    cfg_path = root / DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILE
    if not cfg_path.is_file():
        print(f"Error: Config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    # 2. Базовая настройка логирования
    logging.basicConfig(
        level=logging.WARNING - 10 * (ns.verbose or 0),
        format="%(levelname).1s:%(name)s: %(message)s",
    )

    # 3. Режим шаблонов
    if ns.context:
        # Загружаем все секции один раз
        try:
            sections = list_sections(cfg_path)
            configs: dict[str, object] = {
                sec: load_config(cfg_path, sec)
                for sec in sections
            }
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

        # Генерируем контекст
        try:
            generate_context(
                context_name=ns.context,
                configs=configs,
                list_only=ns.list_included,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 4. Режим списка секций
    if ns.list_sections:
        try:
            for sec in list_sections(cfg_path):
                print(sec)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # 5. Обычный режим листинга одной секции
    try:
        cfg = load_config(cfg_path, ns.section)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Применяем CLI-overrides
    # код-фенсинг
    cfg.code_fence = ns.code_fence
    # max_heading_level (только если явно задан)
    if ns.max_heading_level is not None:
        cfg.markdown.max_heading_level = ns.max_heading_level

    generate_listing(
        root=root,
        cfg=cfg,
        mode=ns.mode,
        list_only=ns.list_included,
    )


if __name__ == "__main__":
    main()

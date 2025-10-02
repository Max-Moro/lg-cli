"""
Тесты контекстуального анализа заголовков с горизонтальными чертами.
"""

from __future__ import annotations

from tests.md_placeholders.conftest import md_project, create_template, render_template
from tests.md_placeholders.test_contextual_analysis import (
    extract_heading_level, assert_heading_level, assert_heading_not_present
)


# ===== Тесты основного сценария с горизонтальными чертами =====

def test_horizontal_rule_resets_context_to_level_1(md_project):
    """
    Тест что горизонтальная черта сбрасывает контекст заголовков до уровня 1.
    """
    root = md_project
    
    create_template(root, "horizontal-rule-reset", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")
    
    result = render_template(root, "ctx:horizontal-rule-reset")
    
    # До горизонтальной черты: плейсхолдеры образуют цепочку под H2
    # strip_h1=FALSE (цепочка), max_heading_level=3 (H2+1)
    # H1 заголовки сохраняются как H3, H2+ повышены на 2
    assert_heading_level(result, "API Reference", 3)    # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "User Guide", 3)       # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "Authentication", 4)   # H2→H4 (повышен на 2)
    assert_heading_level(result, "Installation", 4)     # H2→H4 (повышен на 2)
    
    # После горизонтальной черты: контекст сброшен до уровня 1
    # strip_h1=false (нет родительского заголовка), max_heading_level=1 
    assert_heading_level(result, "Main Project", 1)     # H1→H1 (оригинальный уровень)
    assert_heading_level(result, "Features", 2)         # H2→H2 (оригинальный уровень)


def test_multiple_horizontal_rules_create_isolated_sections(md_project):
    """
    Тест что несколько горизонтальных черт создают изолированные секции.
    """
    root = md_project
    
    create_template(root, "multiple-rules", """# Documentation

## Section A
${md:docs/api}

---

## Section B  
${md:docs/guide}

---

## Section C
${md:README}
""")
    
    result = render_template(root, "ctx:multiple-rules")
    
    # Каждый плейсхолдер изолирован заголовками H2
    # strip_h1=true (разделены заголовками), max_heading_level=3 (H2+1)
    
    # api.md в Section A
    assert_heading_not_present(result, "API Reference")      # H1 удален  
    assert_heading_level(result, "Authentication", 3)        # H2→H3
    
    # guide.md в Section B  
    assert_heading_not_present(result, "User Guide")         # H1 удален
    assert_heading_level(result, "Installation", 3)          # H2→H3
    
    # README.md в Section C
    assert_heading_not_present(result, "Main Project")       # H1 удален
    assert_heading_level(result, "Features", 3)              # H2→H3


def test_horizontal_rule_different_formats(md_project):
    """
    Тест различных форматов горизонтальных черт: ---, ***, ___.
    """
    root = md_project
    
    create_template(root, "rule-formats", """# Documentation

## Part 1
${md:docs/api}

---

${md:docs/guide}

***

${md:docs/changelog}

___

${md:README}
""")
    
    result = render_template(root, "ctx:rule-formats")
    
    # Все форматы горизонтальных черт должны работать одинаково
    # Каждый плейсхолдер изолирован, контекст сброшен до уровня 1
    
    # После первой черты (---)
    assert_heading_level(result, "User Guide", 1)        # H1→H1 (корневой)
    assert_heading_level(result, "Installation", 2)      # H2→H2 (корневой)
    
    # После второй черты (***)  
    assert_heading_level(result, "v1.0.0", 1)           # H2→H1 (нет H1 в файле, H2 становится корневым)
    assert_heading_level(result, "v0.9.0", 1)           # H2→H1
    
    # После третьей черты (___)
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (корневой)
    assert_heading_level(result, "Features", 2)          # H2→H2 (корневой)


# ===== Тесты прерывания цепочек горизонтальными чертами =====

def test_horizontal_rule_breaks_placeholder_chain(md_project):
    """
    Тест что горизонтальная черта прерывает цепочку плейсхолдеров.
    
    До черты: цепочка (strip_h1=false)
    После черты: изолированный плейсхолдер (strip_h1=false, но уровень 1)
    """
    root = md_project
    
    create_template(root, "chain-break", """# Documentation  

## Connected Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")
    
    result = render_template(root, "ctx:chain-break")
    
    # До черты: цепочка плейсхолдеров под H2
    # strip_h1=FALSE (цепочка), max_heading_level=3
    # H1 заголовки сохраняются как H3, H2+ повышены на 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "Authentication", 4)    # H2→H4 (повышен на 2)
    
    # После черты: изолированный плейсхолдер, контекст сброшен
    # strip_h1=false (нет родительского заголовка), max_heading_level=1
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (корневой)
    assert_heading_level(result, "Features", 2)          # H2→H2 (корневой)


def test_chain_before_and_after_horizontal_rule(md_project):
    """
    Тест цепочек плейсхолдеров до и после горизонтальной черты.
    """
    root = md_project
    
    create_template(root, "chains-separated", """# Main Document

## Before Rule Section
${md:docs/api}
${md:docs/guide}

---

## After Rule Section  
${md:docs/changelog}
${md:README}
""")
    
    result = render_template(root, "ctx:chains-separated")
    
    # До горизонтальной черты: цепочка под H2
    # strip_h1=FALSE (цепочка), max_heading_level=3
    # H1 заголовки сохраняются как H3, H2+ повышены на 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (цепочка, сохранен)
    
    # После горизонтальной черты: новая цепочка под H2 (но с новым контекстом)
    # strip_h1=FALSE (цепочка), max_heading_level=3  
    # changelog.md не имеет H1, README.md имеет H1 и он сохраняется
    assert_heading_level(result, "v1.0.0", 3)           # H2→H3 (changelog без H1, повышен на 1)
    assert_heading_level(result, "Main Project", 3)      # H1→H3 (цепочка, сохранен)


# ===== Тесты взаимодействия с плейсхолдерами в заголовках =====

def test_horizontal_rule_with_placeholder_in_heading(md_project):
    """
    Тест горизонтальной черты в сочетании с плейсхолдерами внутри заголовков.
    """
    root = md_project
    
    create_template(root, "rule-inline-heading", """# Project Documentation

## Normal Section
${md:docs/api}

---

## ${md:docs/guide}

Some additional content.

## Regular Section Again
${md:README}
""")
    
    result = render_template(root, "ctx:rule-inline-heading")
    
    # До черты: обычный плейсхолдер под H2
    assert_heading_not_present(result, "API Reference")  # H1 удален (разделен)
    assert_heading_level(result, "Authentication", 3)    # H2→H3
    
    # После черты: плейсхолдер в заголовке H2
    assert_heading_level(result, "User Guide", 2)        # H1 заменил содержимое H2
    assert_heading_level(result, "Installation", 3)      # H2→H3 (под inline заголовком)
    
    # Еще один плейсхолдер после inline заголовка
    assert_heading_not_present(result, "Main Project")   # H1 удален (разделен)
    assert_heading_level(result, "Features", 3)          # H2→H3


# ===== Тесты edge cases =====

def test_horizontal_rule_at_document_start(md_project):
    """
    Тест горизонтальной черты в начале документа.
    """
    root = md_project
    
    create_template(root, "rule-at-start", """---

${md:README}

## Additional Section
${md:docs/api}
""")
    
    result = render_template(root, "ctx:rule-at-start")
    
    # README в самом начале после черты: корневой уровень
    assert_heading_level(result, "Main Project", 1)      # H1→H1
    assert_heading_level(result, "Features", 2)          # H2→H2
    
    # api.md под H2: разделен заголовком
    assert_heading_not_present(result, "API Reference")  # H1 удален
    assert_heading_level(result, "Authentication", 3)    # H2→H3


def test_horizontal_rule_at_document_end(md_project):
    """
    Тест горизонтальной черты в конце документа.
    """
    root = md_project
    
    create_template(root, "rule-at-end", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}

---
""")
    
    result = render_template(root, "ctx:rule-at-end")
    
    # Цепочка плейсхолдеров до черты должна работать нормально
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (цепочка)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (цепочка)
    assert_heading_level(result, "Authentication", 4)    # H2→H4
    assert_heading_level(result, "Installation", 4)      # H2→H4


def test_horizontal_rule_inside_fenced_block_ignored(md_project):
    """
    Тест что горизонтальные черты внутри fenced-блоков игнорируются.
    """
    root = md_project
    
    create_template(root, "rule-in-fenced", """# Documentation

## Code Example

```markdown
# Sample Document

---

This is not a real horizontal rule.
```

## Continuous Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")
    
    result = render_template(root, "ctx:rule-in-fenced")
    
    # Черта в fenced-блоке не должна влиять на анализ
    # api.md и guide.md должны образовывать цепочку под H2
    # strip_h1=FALSE (цепочка), max_heading_level=3
    # H1 заголовки сохраняются как H3, H2+ повышены на 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (цепочка, сохранен)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (цепочка, сохранен)
    
    # README после реальной черты: сброшенный контекст
    # strip_h1=false (нет родительского заголовка), max_heading_level=1
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (корневой)
    assert_heading_level(result, "Features", 2)          # H2→H2 (корневой)


# ===== Тесты совместимости с существующей логикой =====

def test_horizontal_rule_preserves_existing_logic_for_regular_cases(md_project):
    """
    Тест что добавление поддержки горизонтальных черт не ломает существующую логику.
    
    Шаблоны без горизонтальных черт должны работать как раньше.
    """
    root = md_project
    
    # Случай 1: разделенные заголовками (должен быть strip_h1=true)
    create_template(root, "backward-compat-separated", """# Documentation

## API Section
${md:docs/api}

## Guide Section  
${md:docs/guide}
""")
    
    separated_result = render_template(root, "ctx:backward-compat-separated")
    
    # Плейсхолдеры разделены → strip_h1=true  
    assert_heading_not_present(separated_result, "API Reference")
    assert_heading_not_present(separated_result, "User Guide")
    assert_heading_level(separated_result, "Authentication", 3)
    assert_heading_level(separated_result, "Installation", 3)
    
    # Случай 2: непрерывная цепочка (должен быть strip_h1=false)
    create_template(root, "backward-compat-chain", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}
""")
    
    chain_result = render_template(root, "ctx:backward-compat-chain")
    
    # Плейсхолдеры образуют цепочку → strip_h1=false
    assert_heading_level(chain_result, "API Reference", 3)    # H1→H3 (сохранен)
    assert_heading_level(chain_result, "User Guide", 3)       # H1→H3 (сохранен) 
    assert_heading_level(chain_result, "Authentication", 4)   # H2→H4
    assert_heading_level(chain_result, "Installation", 4)     # H2→H4


def test_explicit_parameters_still_override_horizontal_rule_logic(md_project):
    """
    Тест что явные параметры всё еще переопределяют логику с горизонтальными чертами.
    """
    root = md_project
    
    create_template(root, "explicit-override-with-rule", """# Documentation

## Section A
${md:docs/api}

---

${md:README, level:3, strip_h1:true}
""")
    
    result = render_template(root, "ctx:explicit-override-with-rule")
    
    # До черты: обычная логика
    assert_heading_not_present(result, "API Reference")  # H1 удален (разделен)
    assert_heading_level(result, "Authentication", 3)    # H2→H3
    
    # После черты: явные параметры переопределяют логику сброса контекста
    assert_heading_not_present(result, "Main Project")   # strip_h1:true форсирован
    assert_heading_level(result, "Features", 3)          # level:3 форсирован (H2→H3)
"""
Tests for section inheritance via extends.

Covers ТЗ §11.1: extends merging, child wins on conflicts, cycle detection.
"""

from __future__ import annotations

import textwrap

import pytest

from tests.infrastructure import (
    write,
    create_mode_meta_section, create_tag_meta_section,
    create_adaptive_section,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig,
)


class TestExtendsBasicMerge:
    """Tests for basic extends merge behavior."""

    def test_child_inherits_parent_mode_sets(self, extends_project):
        """Section inheriting from meta-section should have parent's mode-sets."""
        from lg.adaptive.listing import list_mode_sets

        root = extends_project

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")

        result = list_mode_sets(root, "test", "com.test.provider")
        mode_set_ids = {ms.id for ms in result.mode_sets}

        assert "ai-interaction" in mode_set_ids
        assert "dev-stage" in mode_set_ids

    def test_child_inherits_parent_tag_sets(self, extends_project):
        """Section inheriting from meta-section should have parent's tag-sets."""
        from lg.adaptive.listing import list_tag_sets

        root = extends_project

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")

        result = list_tag_sets(root, "test")
        tag_set_ids = {ts.id for ts in result.tag_sets}

        assert "language" in tag_set_ids

    def test_child_wins_mode_override(self, tmp_path):
        """When child redefines a mode, child's version should win."""
        root = tmp_path

        # Parent with "Ask Basic" title
        create_mode_meta_section(root, "parent-modes", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(
                        title="Ask Basic",
                        runs={"com.test.provider": "--basic"},
                    ),
                }
            )
        })

        # Child overrides ask with "Ask Advanced"
        create_adaptive_section(root, "child-modes",
            extends=["parent-modes"],
            mode_sets={
                "ai-interaction": ModeSetConfig(
                    title="AI Interaction",
                    modes={
                        "ask": ModeConfig(
                            title="Ask Advanced",
                            runs={"com.test.provider": "--advanced"},
                        ),
                    }
                )
            },
        )

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["child-modes"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_mode_sets
        result = list_mode_sets(root, "test", "com.test.provider")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        ask_mode = next(m for m in ai_set.modes if m.id == "ask")

        assert ask_mode.title == "Ask Advanced"
        assert ask_mode.runs["com.test.provider"] == "--advanced"

    def test_child_adds_new_modes_to_parent_set(self, tmp_path):
        """Child should be able to add new modes to parent's mode-set."""
        root = tmp_path

        # Parent with ask mode only
        create_mode_meta_section(root, "parent-modes", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(
                        title="Ask",
                        runs={"com.test.provider": "--ask"},
                    ),
                }
            )
        })

        # Child adds agent mode to same set
        create_adaptive_section(root, "child-modes",
            extends=["parent-modes"],
            mode_sets={
                "ai-interaction": ModeSetConfig(
                    title="AI Interaction",
                    modes={
                        "agent": ModeConfig(
                            title="Agent",
                            tags=["agent"],
                            runs={"com.test.provider": "--agent"},
                        ),
                    }
                )
            },
        )

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["child-modes"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_mode_sets
        result = list_mode_sets(root, "test", "com.test.provider")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        mode_ids = {m.id for m in ai_set.modes}

        # Both parent's and child's modes should be present
        assert "ask" in mode_ids
        assert "agent" in mode_ids

    def test_multi_level_extends(self, tmp_path):
        """Three-level inheritance: grandparent -> parent -> child."""
        root = tmp_path

        # Grandparent: ask
        create_mode_meta_section(root, "grandparent", {
            "ai-interaction": ModeSetConfig(
                title="AI",
                modes={
                    "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
                }
            )
        })

        # Parent extends grandparent, adds agent
        create_adaptive_section(root, "parent",
            extends=["grandparent"],
            mode_sets={
                "ai-interaction": ModeSetConfig(
                    title="AI",
                    modes={
                        "agent": ModeConfig(title="Agent", runs={"com.test.provider": "--agent"}),
                    }
                )
            },
        )

        # Child extends parent, adds plan
        create_adaptive_section(root, "child",
            extends=["parent"],
            mode_sets={
                "ai-interaction": ModeSetConfig(
                    title="AI",
                    modes={
                        "plan": ModeConfig(title="Plan", runs={"com.test.provider": "--plan"}),
                    }
                )
            },
        )

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["child"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_mode_sets
        result = list_mode_sets(root, "test", "com.test.provider")

        ai_set = next(ms for ms in result.mode_sets if ms.id == "ai-interaction")
        mode_ids = {m.id for m in ai_set.modes}

        # All three levels should be merged
        assert "ask" in mode_ids     # from grandparent
        assert "agent" in mode_ids   # from parent
        assert "plan" in mode_ids    # from child

    def test_child_wins_tag_override(self, tmp_path):
        """When child redefines a tag, child's version should win."""
        root = tmp_path

        # Parent tag-set with "Python 2" title
        create_tag_meta_section(root, "parent-tags", {
            "language": TagSetConfig(
                title="Languages",
                tags={"python": TagConfig(title="Python 2")}
            )
        })

        # Child overrides with "Python 3"
        create_adaptive_section(root, "child-tags",
            extends=["parent-tags"],
            tag_sets={
                "language": TagSetConfig(
                    title="Languages",
                    tags={"python": TagConfig(title="Python 3")}
                )
            },
        )

        # Integration mode-set (required)
        create_mode_meta_section(root, "ai-modes", {
            "ai": ModeSetConfig(
                title="AI",
                modes={"ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"})}
            )
        })

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["ai-modes", "child-tags"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.listing import list_tag_sets
        result = list_tag_sets(root, "test")

        lang_set = next(ts for ts in result.tag_sets if ts.id == "language")
        python_tag = next(t for t in lang_set.tags if t.id == "python")

        assert python_tag.title == "Python 3"


class TestExtendsCrossScope:
    """Tests for extends resolution across scopes (federated repository)."""

    def test_list_sections_resolves_extends_in_child_scope(self, tmp_path):
        """
        Bug: _resolve_adaptive_from_resolved() passed scope_dir=root instead of
        resolved.scope_dir, causing extends lookup for parent sections
        to search the wrong scope.

        Setup:
        - Root scope has context including cross-scope context ${ctx@child:common}
        - Child scope has meta-section 'tags' and section 'src' that extends 'tags'
        - list_sections must resolve extends in the child scope, not root
        """
        from lg.listing import list_sections

        root = tmp_path
        child_dir = root / "child"

        # -- Root scope --
        # Integration mode-set (required for context validation)
        create_mode_meta_section(root, "ai-modes", {
            "ai-interaction": ModeSetConfig(
                title="AI Interaction",
                modes={
                    "ask": ModeConfig(
                        title="Ask",
                        runs={"com.test.provider": "--ask"},
                    ),
                }
            )
        })

        # Root context referencing cross-scope context
        write(root / "lg-cfg" / "main.ctx.md", textwrap.dedent("""\
        ---
        include: ["ai-modes"]
        ---
        # Main
        ${ctx@child:common}
        """))

        # -- Child scope --
        # Meta-section with tag-sets (extends target)
        create_tag_meta_section(child_dir, "tags", {
            "language": TagSetConfig(
                title="Languages",
                tags={"python": TagConfig(title="Python")}
            )
        })

        # Section extending meta-section in same child scope
        write(child_dir / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["tags"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        # Child context referencing child section
        write(child_dir / "lg-cfg" / "common.ctx.md", "# Common\n${src}\n")

        # Source file so section is non-empty
        write(child_dir / "app.py", "x = 1\n")

        # Act: should not raise SectionNotFoundInExtendsError
        result = list_sections(root, context="main")

        # Assert: child section present with inherited tag-set
        # Cross-scope sections include @scope_rel: prefix for disambiguation
        section_names = [s.name for s in result.sections]
        assert "@child:src" in section_names

        src_info = next(s for s in result.sections if s.name == "@child:src")
        tag_set_ids = {ts.id for ts in getattr(src_info, "tag_sets", [])}
        assert "language" in tag_set_ids


class TestExtendsCycleDetection:
    """Tests for cycle detection in extends chains."""

    def test_direct_cycle_raises_error(self, tmp_path):
        """Cycle A -> B -> A should raise ExtendsCycleError."""
        root = tmp_path

        # A extends B
        create_adaptive_section(root, "section-a",
            extends=["section-b"],
            mode_sets={
                "ms-a": ModeSetConfig(title="A", modes={
                    "m": ModeConfig(title="M", runs={"com.test.provider": "--a"})
                })
            },
        )

        # B extends A
        create_adaptive_section(root, "section-b",
            extends=["section-a"],
            mode_sets={
                "ms-b": ModeSetConfig(title="B", modes={
                    "m": ModeConfig(title="M")
                })
            },
        )

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["section-a"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.errors import ExtendsCycleError
        from lg.adaptive.listing import list_mode_sets

        with pytest.raises(ExtendsCycleError):
            list_mode_sets(root, "test", "com.test.provider")

    def test_self_reference_raises_error(self, tmp_path):
        """Section extending itself should raise ExtendsCycleError."""
        root = tmp_path

        create_adaptive_section(root, "self-ref",
            extends=["self-ref"],
            mode_sets={
                "ms": ModeSetConfig(title="MS", modes={
                    "m": ModeConfig(title="M", runs={"com.test.provider": "--m"})
                })
            },
        )

        write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
        src:
          extends: ["self-ref"]
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/**"
        """))

        write(root / "lg-cfg" / "test.ctx.md", "# Test\n${src}\n")
        write(root / "main.py", "x = 1\n")

        from lg.adaptive.errors import ExtendsCycleError
        from lg.adaptive.listing import list_mode_sets

        with pytest.raises(ExtendsCycleError):
            list_mode_sets(root, "test", "com.test.provider")

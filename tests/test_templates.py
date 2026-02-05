"""Tests for skill template system."""

import pytest

from sutras.core.templates import (
    BUILT_IN_TEMPLATES,
    get_template,
    list_templates,
    render_template,
)


class TestListTemplates:
    def test_returns_all_built_ins(self):
        templates = list_templates()
        names = [t.name for t in templates]
        assert "default" in names
        assert "code-review" in names
        assert "api-integration" in names
        assert "data-analysis" in names
        assert "automation" in names

    def test_sorted_by_name(self):
        templates = list_templates()
        names = [t.name for t in templates]
        assert names == sorted(names)

    def test_all_have_descriptions(self):
        for tmpl in list_templates():
            assert tmpl.description, f"Template '{tmpl.name}' has no description"


class TestGetTemplate:
    def test_get_existing(self):
        tmpl = get_template("default")
        assert tmpl.name == "default"

    def test_get_code_review(self):
        tmpl = get_template("code-review")
        assert tmpl.name == "code-review"
        assert "code review" in tmpl.description.lower()

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown template 'nonexistent'"):
            get_template("nonexistent")

    def test_error_message_lists_available(self):
        with pytest.raises(ValueError, match="default"):
            get_template("nonexistent")


class TestRenderTemplate:
    def test_render_default(self):
        tmpl = get_template("default")
        files = render_template(tmpl, "my-skill", "A test skill", "Test Author")
        assert "SKILL.md" in files
        assert "sutras.yaml" in files
        assert "examples.md" in files

    def test_skill_md_has_name(self):
        tmpl = get_template("default")
        files = render_template(tmpl, "my-skill", "A test skill", "Test Author")
        assert "name: my-skill" in files["SKILL.md"]

    def test_skill_md_has_description(self):
        tmpl = get_template("default")
        files = render_template(tmpl, "my-skill", "A test skill", "Test Author")
        assert "description: A test skill" in files["SKILL.md"]

    def test_sutras_yaml_has_author(self):
        tmpl = get_template("default")
        files = render_template(tmpl, "my-skill", "A test skill", "Test Author")
        assert 'author: "Test Author"' in files["sutras.yaml"]

    def test_title_formatting(self):
        tmpl = get_template("default")
        files = render_template(tmpl, "my-cool-skill", "desc", "Author")
        assert "My Cool Skill" in files["SKILL.md"]
        assert "My Cool Skill" in files["examples.md"]

    def test_code_review_has_allowed_tools(self):
        tmpl = get_template("code-review")
        files = render_template(tmpl, "reviewer", "Reviews code", "Author")
        assert "allowed-tools:" in files["SKILL.md"]
        assert "Read" in files["SKILL.md"]

    def test_code_review_has_tests(self):
        tmpl = get_template("code-review")
        files = render_template(tmpl, "reviewer", "Reviews code", "Author")
        assert "tests:" in files["sutras.yaml"]
        assert "cases:" in files["sutras.yaml"]

    def test_all_templates_render_without_error(self):
        for tmpl in list_templates():
            files = render_template(tmpl, "test-skill", "A test", "Author")
            assert "SKILL.md" in files
            assert "sutras.yaml" in files
            assert "examples.md" in files

    def test_all_templates_have_valid_yaml_frontmatter(self):
        for tmpl in list_templates():
            files = render_template(tmpl, "test-skill", "A test", "Author")
            skill_md = files["SKILL.md"]
            assert skill_md.startswith("---\n"), (
                f"Template '{tmpl.name}' SKILL.md missing frontmatter"
            )
            assert skill_md.count("---") >= 2, (
                f"Template '{tmpl.name}' SKILL.md incomplete frontmatter"
            )

    def test_all_templates_have_version_in_yaml(self):
        for tmpl in list_templates():
            files = render_template(tmpl, "test-skill", "A test", "Author")
            assert "version:" in files["sutras.yaml"], f"Template '{tmpl.name}' missing version"


class TestBuiltInTemplates:
    def test_registry_populated(self):
        assert len(BUILT_IN_TEMPLATES) >= 5

    def test_all_templates_have_required_fields(self):
        for name, tmpl in BUILT_IN_TEMPLATES.items():
            assert tmpl.name == name
            assert tmpl.skill_md
            assert tmpl.sutras_yaml
            assert tmpl.examples_md

"""Tests for skill naming system."""

import pytest

from sutras.core.naming import SkillName, validate_namespace, validate_skill_name


class TestSkillName:
    def test_parse_scoped_name(self):
        name = SkillName.parse("@user/my-skill")
        assert name.namespace == "user"
        assert name.name == "my-skill"
        assert name.is_scoped is True

    def test_parse_bare_name(self):
        name = SkillName.parse("my-skill")
        assert name.namespace is None
        assert name.name == "my-skill"
        assert name.is_scoped is False

    def test_parse_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            SkillName.parse("")

    def test_parse_invalid_scoped_format(self):
        with pytest.raises(ValueError, match="Invalid scoped skill name"):
            SkillName.parse("@invalid")

    def test_parse_invalid_scoped_missing_name(self):
        with pytest.raises(ValueError, match="Invalid scoped skill name"):
            SkillName.parse("@user/")

    def test_parse_slash_without_at(self):
        with pytest.raises(ValueError, match="Use '@namespace/name' format"):
            SkillName.parse("user/skill")

    def test_parse_invalid_characters(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            SkillName.parse("my skill")

    def test_str_scoped(self):
        name = SkillName(namespace="user", name="skill", is_scoped=True)
        assert str(name) == "@user/skill"

    def test_str_bare(self):
        name = SkillName(namespace=None, name="skill", is_scoped=False)
        assert str(name) == "skill"

    def test_to_filesystem_name_scoped(self):
        name = SkillName.parse("@user/my-skill")
        assert name.to_filesystem_name() == "user_my-skill"

    def test_to_filesystem_name_bare(self):
        name = SkillName.parse("my-skill")
        assert name.to_filesystem_name() == "my-skill"

    def test_valid_characters_in_namespace(self):
        name = SkillName.parse("@user-name_123/skill")
        assert name.namespace == "user-name_123"

    def test_valid_characters_in_skill_name(self):
        name = SkillName.parse("@user/skill-name_123")
        assert name.name == "skill-name_123"


class TestValidateNamespace:
    def test_valid_namespace(self):
        validate_namespace("user")
        validate_namespace("my-org")
        validate_namespace("user_123")

    def test_empty_namespace(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_namespace("")

    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            validate_namespace("user name")

    def test_namespace_with_at(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            validate_namespace("@user")


class TestValidateSkillName:
    def test_valid_name(self):
        validate_skill_name("my-skill")
        validate_skill_name("skill_123")
        validate_skill_name("MySkill")

    def test_empty_name(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_skill_name("")

    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            validate_skill_name("my skill")

    def test_scoped_name_rejected(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            validate_skill_name("@user/skill")

    def test_slash_rejected(self):
        with pytest.raises(ValueError, match="Only alphanumeric"):
            validate_skill_name("user/skill")

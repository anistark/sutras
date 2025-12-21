"""Tests for skill loading and management."""

import pytest

from sutras import Skill, SkillLoader, SkillMetadata


def test_skill_metadata_creation():
    """Test creating skill metadata."""
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill",
    )

    assert metadata.name == "test-skill"
    assert metadata.description == "A test skill"
    assert metadata.allowed_tools is None


def test_skill_metadata_with_tools():
    """Test metadata with allowed tools."""
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill",
        allowed_tools=["Read", "Write"],
    )

    assert metadata.allowed_tools == ["Read", "Write"]


def test_skill_loader_discover(tmp_path):
    """Test skill discovery."""
    # Create a temporary skill
    skills_dir = tmp_path / ".claude" / "skills"
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir(parents=True)

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
---

# Test Skill

Test instructions.
""")

    # Create loader
    loader = SkillLoader(search_paths=[skills_dir], include_global=False, include_project=False)

    # Discover skills
    skills = loader.discover()
    assert "test-skill" in skills


def test_skill_loading(tmp_path):
    """Test loading a skill."""
    # Create a temporary skill
    skills_dir = tmp_path / ".claude" / "skills"
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir(parents=True)

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
allowed-tools: Read, Write, Bash
---

# Test Skill

Test instructions here.
""")

    # Create sutras.yaml
    sutras_yaml = skill_dir / "sutras.yaml"
    sutras_yaml.write_text("""version: "1.0.0"
author: "Test Author"
license: "MIT"
""")

    # Create loader and load skill
    loader = SkillLoader(search_paths=[skills_dir], include_global=False, include_project=False)
    skill = loader.load("test-skill")

    assert skill.name == "test-skill"
    assert skill.description == "A test skill for unit testing"
    assert skill.allowed_tools == ["Read", "Write", "Bash"]
    assert skill.version == "1.0.0"
    assert skill.author == "Test Author"


def test_skill_parse_invalid_frontmatter():
    """Test that invalid SKILL.md raises error."""
    content = "# No frontmatter\n\nJust content"

    with pytest.raises(ValueError, match="must contain YAML frontmatter"):
        Skill._parse_skill_md(content)


def test_skill_parse_missing_name():
    """Test that missing name field raises error."""
    content = """---
description: Missing name field
---

# Content
"""

    with pytest.raises(ValueError, match="must include 'name' field"):
        Skill._parse_skill_md(content)


def test_skill_parse_missing_description():
    """Test that missing description field raises error."""
    content = """---
name: test-skill
---

# Content
"""

    with pytest.raises(ValueError, match="must include 'description' field"):
        Skill._parse_skill_md(content)

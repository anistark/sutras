"""Tests for skill packaging."""

import json

from sutras import Skill, SkillBuilder


def test_manifest_serializes_mixed_dependencies(tmp_path):
    skill_dir = tmp_path / "depskill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: depskill\ndescription: Skill with mixed dependencies\n---\n\nBody\n"
    )
    (skill_dir / "sutras.yaml").write_text(
        """version: "1.0.0"
capabilities:
  dependencies:
    - "@acme/plain"
    - name: "@acme/ranged"
      version: "^1.0.0"
"""
    )
    manifest = SkillBuilder(Skill.load(skill_dir), output_dir=tmp_path / "out").create_manifest()

    deps = json.loads(json.dumps(manifest))["dependencies"]
    assert deps[0] == "@acme/plain"
    assert deps[1]["name"] == "@acme/ranged"
    assert deps[1]["version"] == "^1.0.0"

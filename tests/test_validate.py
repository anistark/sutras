"""Tests for the `sutras validate` command and skill load errors."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from sutras import Skill, SkillLoadError
from sutras.cli.main import cli
from sutras.core.validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    extract_file_references,
    is_known_tool,
    parse_tool_entry,
)

VALID_SKILL_MD = """---
name: {name}
description: A skill used to exercise the validate command in tests
---

Detailed instructions for the skill.
"""

FULL_SUTRAS_YAML = """version: "1.0.0"
author: "Test Author"
license: "Apache-2.0"
distribution:
  tags: [testing]
  category: testing
"""


def _make_skill(root: Path, name: str, sutras_yaml: str | None = None) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(VALID_SKILL_MD.format(name=name))
    if sutras_yaml is not None:
        (skill_dir / "sutras.yaml").write_text(sutras_yaml)
    return skill_dir


def _validate(*args: str):
    return CliRunner().invoke(cli, ["validate", *args])


class TestSkillLoadErrors:
    def test_invalid_yaml_raises_skill_load_error(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "bad", "version: [unclosed\n")
        with pytest.raises(SkillLoadError) as exc:
            Skill.load(skill_dir)
        assert exc.value.file == "sutras.yaml"
        assert "Invalid YAML" in exc.value.problems[0]

    def test_empty_sutras_yaml_raises_skill_load_error(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "empty", "")
        with pytest.raises(SkillLoadError, match="File is empty"):
            Skill.load(skill_dir)

    def test_non_mapping_sutras_yaml(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "list", "- 1.0.0\n")
        with pytest.raises(SkillLoadError, match="must be a YAML mapping"):
            Skill.load(skill_dir)

    def test_schema_errors_listed_per_field(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "schema", "author: 123\n")
        with pytest.raises(SkillLoadError) as exc:
            Skill.load(skill_dir)
        joined = "\n".join(exc.value.problems)
        assert "'version'" in joined
        assert "'author'" in joined

    def test_missing_name_and_description_reported_together(self, tmp_path):
        skill_dir = tmp_path / "nofields"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nallowed-tools: Read\n---\n\nBody\n")
        with pytest.raises(SkillLoadError) as exc:
            Skill.load(skill_dir)
        assert len(exc.value.problems) == 2

    def test_skill_load_error_is_value_error(self):
        assert issubclass(SkillLoadError, ValueError)

    def test_non_string_name_is_coerced(self, tmp_path):
        skill_dir = tmp_path / "numeric"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: 123\ndescription: null\n---\n\nBody\n")
        skill = Skill.load(skill_dir)
        assert skill.name == "123"
        assert skill.description == ""


class TestValidateCommand:
    def test_valid_skill_passes(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "good", FULL_SUTRAS_YAML)
        result = _validate(str(skill_dir))
        assert result.exit_code == 0, result.output
        assert "is valid" in result.output

    def test_bad_yaml_is_reported_not_crashed(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "bad", "version: [unclosed\n")
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert not isinstance(result.exception, (TypeError, AttributeError))
        assert "sutras.yaml could not be parsed" in result.output
        assert "[abi] Invalid YAML" in result.output

    def test_empty_sutras_yaml_is_reported(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "empty", "")
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "[abi] File is empty" in result.output

    def test_missing_version_is_reported(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "nover", 'author: "Someone"\n')
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "[abi] 'version': Field required" in result.output

    def test_missing_license_warns(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "nolic", 'version: "1.0.0"\nauthor: "A"\n')
        result = _validate(str(skill_dir))
        assert "Missing 'license' field" in result.output

    def test_explicit_license_does_not_warn(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "lic", FULL_SUTRAS_YAML)
        result = _validate(str(skill_dir))
        assert "Missing 'license' field" not in result.output

    @pytest.mark.parametrize("version", ["1.0.0garbage", "v1.0.0", "01.0.0", "1.0"])
    def test_invalid_semver_rejected(self, tmp_path, version):
        skill_dir = _make_skill(tmp_path, "semver", f'version: "{version}"\n')
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "is not valid semver" in result.output

    @pytest.mark.parametrize("version", ["0.1.0", "1.0.0-beta.1"])
    def test_valid_semver_accepted(self, tmp_path, version):
        skill_dir = _make_skill(tmp_path, "semver", f'version: "{version}"\n')
        result = _validate(str(skill_dir))
        assert "is not valid semver" not in result.output

    def test_all_continues_past_broken_skill(self, tmp_path):
        _make_skill(tmp_path, "aaa-broken", "version: [unclosed\n")
        _make_skill(tmp_path, "bbb-good", FULL_SUTRAS_YAML)
        _make_skill(tmp_path, "ccc-empty", "")
        result = _validate("--all", "--path", str(tmp_path))
        assert result.exit_code != 0
        assert "Skill 'bbb-good' is valid" in result.output
        assert "Validated 3 skill(s)" in result.output
        assert "1 passed" in result.output
        assert "2 failed" in result.output
        assert "aaa-broken, ccc-empty" in result.output

    def test_unknown_skill_name(self, tmp_path):
        result = _validate("does-not-exist", "--path", str(tmp_path))
        assert result.exit_code != 0
        assert "not found" in result.output


def _write_skill_md(
    skill_dir: Path, frontmatter: str, body: str = "Detailed instructions."
) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n{body}\n")


DESC = "description: A skill used to exercise the validate command in tests"


class TestValidationHelpers:
    @pytest.mark.parametrize(
        ("entry", "expected"),
        [
            ("Read", "Read"),
            ("Bash(git:*)", "Bash"),
            ("Bash(git add:*)", "Bash"),
            ("mcp__github__create_issue", "mcp__github__create_issue"),
            ("Bash(git:*) Read", None),
            ("123", None),
        ],
    )
    def test_parse_tool_entry(self, entry, expected):
        assert parse_tool_entry(entry) == expected

    def test_is_known_tool(self):
        assert is_known_tool("Read")
        assert is_known_tool("mcp__server__tool")
        assert not is_known_tool("Reed")

    def test_extract_file_references(self):
        markdown = """
See [reference](reference.md) and [section](examples.md#usage).
![diagram](images/flow%20chart.png "Flow")
[site](https://example.com) [mail](mailto:a@b.c) [anchor](#top) [abs](/etc/passwd)
Duplicate [again](reference.md). Inline `[code](ignored.md)`.

```markdown
[fenced](also-ignored.md)
```
"""
        assert extract_file_references(markdown) == [
            "reference.md",
            "examples.md",
            "images/flow chart.png",
        ]


class TestValidateNewChecks:
    def test_name_too_long_is_error(self, tmp_path):
        name = "a" * (MAX_NAME_LENGTH + 1)
        _write_skill_md(tmp_path / name, f"name: {name}\n{DESC}")
        result = _validate(str(tmp_path / name))
        assert result.exit_code != 0
        assert f"Name is {MAX_NAME_LENGTH + 1} chars" in result.output

    def test_description_too_long_is_error(self, tmp_path):
        desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        _write_skill_md(tmp_path / "long", f"name: long\ndescription: {desc}")
        result = _validate(str(tmp_path / "long"))
        assert result.exit_code != 0
        assert f"Description is {MAX_DESCRIPTION_LENGTH + 1} chars" in result.output

    def test_name_directory_mismatch_warns(self, tmp_path):
        _write_skill_md(tmp_path / "folder", f"name: other\n{DESC}")
        result = _validate(str(tmp_path / "folder"))
        assert "does not match directory name 'folder'" in result.output

    def test_scoped_name_matches_bare_directory(self, tmp_path):
        _write_skill_md(tmp_path / "tool", f"name: '@acme/tool'\n{DESC}")
        result = _validate(str(tmp_path / "tool"))
        assert "does not match directory name" not in result.output
        assert "non-standard characters" not in result.output

    def test_dot_path_uses_cwd_name(self, tmp_path, monkeypatch):
        _write_skill_md(tmp_path / "here", f"name: here\n{DESC}")
        monkeypatch.chdir(tmp_path / "here")
        result = _validate(".")
        assert "does not match directory name" not in result.output

    def test_unknown_and_malformed_tools_warn(self, tmp_path):
        _write_skill_md(
            tmp_path / "tools", f"name: tools\n{DESC}\nallowed-tools: Read, Reed, Bash(git:*), 9x"
        )
        result = _validate(str(tmp_path / "tools"), "--strict")
        assert result.exit_code != 0
        assert "Unknown tool 'Reed' in allowed-tools" in result.output
        assert "Malformed allowed-tools entry '9x'" in result.output
        assert "'Bash'" not in result.output

    def test_capabilities_tools_and_dependencies(self, tmp_path):
        skill_dir = _make_skill(
            tmp_path,
            "deps",
            """version: "1.0.0"
capabilities:
  tools: [Read, Wrte]
  dependencies:
    - "@acme/good"
    - "bare-dep"
    - name: "@acme/ranged"
      version: ">=1.0.0 <2.0.0"
    - name: "@acme/badver"
      version: "^one"
    - name: "@bad/name/extra"
""",
        )
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "Unknown tool 'Wrte' in capabilities.tools" in result.output
        assert "Dependency 'bare-dep' is not scoped" in result.output
        assert "Invalid version constraint '^one'" in result.output
        assert "Invalid dependency name" in result.output
        assert "2 valid dependencies" in result.output

    def test_file_references(self, tmp_path):
        skill_dir = tmp_path / "refs"
        _write_skill_md(
            skill_dir,
            f"name: refs\n{DESC}",
            "Read [ok](examples.md), [gone](missing.md), [nested](docs/guide.md), "
            "[outside](../shared.md).",
        )
        (skill_dir / "examples.md").write_text("examples")
        (skill_dir / "docs").mkdir()
        (skill_dir / "docs" / "guide.md").write_text("guide")
        (tmp_path / "shared.md").write_text("shared")
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "[files] SKILL.md links to missing file 'missing.md'" in result.output
        assert "'docs/guide.md', which `sutras build` won't package" in result.output
        assert "'../shared.md', outside the skill directory" in result.output
        assert "1 linked file(s) found" in result.output

    def test_missing_dataset_and_fixtures(self, tmp_path):
        skill_dir = _make_skill(
            tmp_path,
            "evalcfg",
            """version: "1.0.0"
tests:
  fixtures_dir: fixtures
eval:
  dataset: data/eval.json
""",
        )
        result = _validate(str(skill_dir))
        assert result.exit_code != 0
        assert "[eval] eval.dataset 'data/eval.json' not found" in result.output
        assert "tests.fixtures_dir 'fixtures' does not exist" in result.output

    def test_default_fixtures_dir_not_checked(self, tmp_path):
        skill_dir = _make_skill(tmp_path, "nofix", 'version: "1.0.0"\ntests:\n  cases: []\n')
        result = _validate(str(skill_dir))
        assert "fixtures_dir" not in result.output

    def test_existing_dataset_passes(self, tmp_path):
        skill_dir = _make_skill(
            tmp_path, "evalok", 'version: "1.0.0"\neval:\n  dataset: eval.json\n'
        )
        (skill_dir / "eval.json").write_text("[]")
        result = _validate(str(skill_dir))
        assert "Eval dataset: eval.json" in result.output

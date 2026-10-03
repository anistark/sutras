"""Skill model combining Anthropic SKILL.md with Sutras ABI."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from sutras.core.abi import SutrasABI


def _describe_yaml_error(error: yaml.YAMLError) -> str:
    """Condense a PyYAML error into a single line with its position."""
    if isinstance(error, yaml.MarkedYAMLError) and error.problem_mark is not None:
        mark = error.problem_mark
        return f"{error.problem} (line {mark.line + 1}, column {mark.column + 1})"
    return str(error).splitlines()[0]


class SkillLoadError(ValueError):
    """Raised when a skill file exists but cannot be parsed.

    Subclasses ValueError so existing callers keep working, while exposing
    structured detail for diagnostics such as ``sutras validate``.

    Attributes:
        file: Name of the file that failed to load (e.g. "SKILL.md", "sutras.yaml")
        problems: Individual problems found in that file
    """

    def __init__(self, file: str, problems: list[str]):
        self.file = file
        self.problems = problems
        super().__init__(f"{file}: " + "; ".join(problems))


@dataclass
class SkillMetadata:
    """Metadata from SKILL.md YAML frontmatter."""

    name: str
    description: str
    allowed_tools: list[str] | None = None

    @classmethod
    def from_frontmatter(cls, frontmatter: dict[str, Any]) -> "SkillMetadata":
        """Parse metadata from YAML frontmatter."""
        allowed_tools = frontmatter.get("allowed-tools")
        if allowed_tools:
            if isinstance(allowed_tools, str):
                # Parse comma-separated string
                allowed_tools = [t.strip() for t in allowed_tools.split(",")]
            elif isinstance(allowed_tools, list):
                allowed_tools = [str(t) for t in allowed_tools]

        name = frontmatter.get("name")
        description = frontmatter.get("description")
        return cls(
            name="" if name is None else str(name),
            description="" if description is None else str(description),
            allowed_tools=allowed_tools,
        )


@dataclass
class Skill:
    """A skill combining Anthropic SKILL.md format with Sutras ABI.

    Represents a complete skill with:
    - SKILL.md: Anthropic Skills format with frontmatter
    - sutras.yaml: Sutras ABI metadata (optional)
    - Supporting files: reference.md, examples.md, etc.
    """

    path: Path
    metadata: SkillMetadata
    instructions: str
    abi: SutrasABI | None = None
    supporting_files: dict[str, Path] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Get skill name."""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Get skill description."""
        return self.metadata.description

    @property
    def allowed_tools(self) -> list[str] | None:
        """Get allowed tools list."""
        return self.metadata.allowed_tools

    @property
    def version(self) -> str | None:
        """Get skill version from ABI."""
        return self.abi.version if self.abi else None

    @property
    def author(self) -> str | None:
        """Get skill author from ABI."""
        return self.abi.author if self.abi else None

    @classmethod
    def load(cls, skill_path: Path) -> "Skill":
        """Load a skill from a directory.

        Args:
            skill_path: Path to skill directory containing SKILL.md

        Returns:
            Loaded Skill instance

        Raises:
            FileNotFoundError: If SKILL.md doesn't exist
            SkillLoadError: If SKILL.md or sutras.yaml is malformed
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        # Parse SKILL.md
        try:
            content = skill_md.read_text()
        except UnicodeDecodeError as e:
            raise SkillLoadError("SKILL.md", [f"File is not valid UTF-8 text: {e}"]) from e
        metadata, instructions = cls._parse_skill_md(content)

        # Load sutras.yaml if present (also check ability.yaml for backward compatibility)
        abi = None
        for abi_name in ("sutras.yaml", "ability.yaml"):
            abi_file = skill_path / abi_name
            if abi_file.exists():
                abi = cls._parse_abi(abi_file)
                break

        # Discover supporting files
        supporting_files = {}
        for file_path in skill_path.glob("*"):
            if file_path.is_file() and file_path.name not in [
                "SKILL.md",
                "sutras.yaml",
                "ability.yaml",
            ]:
                supporting_files[file_path.name] = file_path

        return cls(
            path=skill_path,
            metadata=metadata,
            instructions=instructions,
            abi=abi,
            supporting_files=supporting_files,
        )

    @staticmethod
    def _parse_abi(abi_file: Path) -> SutrasABI:
        """Parse and validate a sutras.yaml (or legacy ability.yaml) file.

        Raises:
            SkillLoadError: If the file is not valid YAML, is not a mapping,
                or does not match the SutrasABI schema
        """
        try:
            abi_data = yaml.safe_load(abi_file.read_text())
        except UnicodeDecodeError as e:
            raise SkillLoadError(abi_file.name, [f"File is not valid UTF-8 text: {e}"]) from e
        except yaml.YAMLError as e:
            raise SkillLoadError(abi_file.name, [f"Invalid YAML: {_describe_yaml_error(e)}"]) from e

        if abi_data is None:
            raise SkillLoadError(abi_file.name, ["File is empty"])
        if not isinstance(abi_data, dict):
            raise SkillLoadError(abi_file.name, ["Top level must be a YAML mapping"])

        try:
            return SutrasABI(**abi_data)
        except ValidationError as e:
            problems = [
                f"'{'.'.join(str(p) for p in err['loc']) or '(root)'}': {err['msg']}"
                for err in e.errors()
            ]
            raise SkillLoadError(abi_file.name, problems) from e

    @staticmethod
    def _parse_skill_md(content: str) -> tuple[SkillMetadata, str]:
        """Parse SKILL.md content into metadata and instructions.

        Args:
            content: SKILL.md file content

        Returns:
            Tuple of (SkillMetadata, instructions)

        Raises:
            SkillLoadError: If frontmatter is missing or malformed
        """
        # Match YAML frontmatter
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            raise SkillLoadError("SKILL.md", ["File must contain YAML frontmatter (---...---)"])

        frontmatter_text = match.group(1)
        instructions = match.group(2).strip()

        # Parse YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            raise SkillLoadError(
                "SKILL.md", [f"Invalid YAML frontmatter: {_describe_yaml_error(e)}"]
            ) from e

        if not isinstance(frontmatter, dict):
            raise SkillLoadError("SKILL.md", ["YAML frontmatter must be a mapping"])

        missing = [
            f"Frontmatter must include '{key}' field"
            for key in ("name", "description")
            if key not in frontmatter
        ]
        if missing:
            raise SkillLoadError("SKILL.md", missing)

        metadata = SkillMetadata.from_frontmatter(frontmatter)
        return metadata, instructions

    def to_dict(self) -> dict[str, Any]:
        """Convert skill to dictionary representation."""
        result = {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "instructions": self.instructions,
        }

        if self.allowed_tools:
            result["allowed_tools"] = self.allowed_tools

        if self.abi:
            result["abi"] = self.abi.model_dump()

        if self.supporting_files:
            result["supporting_files"] = {
                name: str(path) for name, path in self.supporting_files.items()
            }

        return result

    def __repr__(self) -> str:
        """String representation."""
        version_str = f" v{self.version}" if self.version else ""
        return f"Skill(name={self.name}{version_str}, path={self.path})"

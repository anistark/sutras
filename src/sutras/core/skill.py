"""Skill model combining Anthropic SKILL.md with Sutras ABI."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sutras.core.abi import SutrasABI


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

        return cls(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
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
            ValueError: If SKILL.md is malformed
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        # Parse SKILL.md
        content = skill_md.read_text()
        metadata, instructions = cls._parse_skill_md(content)

        # Load sutras.yaml if present (also check ability.yaml for backward compatibility)
        abi = None
        sutras_yaml = skill_path / "sutras.yaml"
        ability_yaml = skill_path / "ability.yaml"
        if sutras_yaml.exists():
            abi_data = yaml.safe_load(sutras_yaml.read_text())
            abi = SutrasABI(**abi_data)
        elif ability_yaml.exists():
            abi_data = yaml.safe_load(ability_yaml.read_text())
            abi = SutrasABI(**abi_data)

        # Discover supporting files
        supporting_files = {}
        for file_path in skill_path.glob("*"):
            if file_path.is_file() and file_path.name not in ["SKILL.md", "sutras.yaml", "ability.yaml"]:
                supporting_files[file_path.name] = file_path

        return cls(
            path=skill_path,
            metadata=metadata,
            instructions=instructions,
            abi=abi,
            supporting_files=supporting_files,
        )

    @staticmethod
    def _parse_skill_md(content: str) -> tuple[SkillMetadata, str]:
        """Parse SKILL.md content into metadata and instructions.

        Args:
            content: SKILL.md file content

        Returns:
            Tuple of (SkillMetadata, instructions)

        Raises:
            ValueError: If frontmatter is missing or malformed
        """
        # Match YAML frontmatter
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            raise ValueError("SKILL.md must contain YAML frontmatter (---...---)")

        frontmatter_text = match.group(1)
        instructions = match.group(2).strip()

        # Parse YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

        if not isinstance(frontmatter, dict):
            raise ValueError("YAML frontmatter must be a dictionary")

        # Validate required fields
        if "name" not in frontmatter:
            raise ValueError("SKILL.md frontmatter must include 'name' field")
        if "description" not in frontmatter:
            raise ValueError("SKILL.md frontmatter must include 'description' field")

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

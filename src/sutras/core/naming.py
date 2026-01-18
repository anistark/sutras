"""Skill naming system for Sutras.

Handles parsing and validation of skill names with namespace support:
- Registry skills: @namespace/skill-name (required for publishing)
- Local skills: skill-name (bare names, local development only)
"""

import re
from dataclasses import dataclass


@dataclass
class SkillName:
    """Parsed skill name with optional namespace."""

    namespace: str | None
    name: str
    is_scoped: bool

    @classmethod
    def parse(cls, skill_name: str) -> "SkillName":
        """Parse a skill name string.

        Args:
            skill_name: Skill name in format '@namespace/name' or 'name'

        Returns:
            Parsed SkillName object

        Raises:
            ValueError: If skill name format is invalid
        """
        if not skill_name:
            raise ValueError("Skill name cannot be empty")

        if skill_name.startswith("@"):
            match = re.match(r"^@([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)$", skill_name)
            if not match:
                raise ValueError(
                    f"Invalid scoped skill name: '{skill_name}'. "
                    f"Expected format: @namespace/skill-name"
                )

            namespace, name = match.groups()
            return cls(namespace=namespace, name=name, is_scoped=True)
        else:
            if "/" in skill_name:
                raise ValueError(
                    f"Invalid skill name: '{skill_name}'. "
                    f"Use '@namespace/name' format for scoped names"
                )

            if not re.match(r"^[a-zA-Z0-9_-]+$", skill_name):
                raise ValueError(
                    f"Invalid skill name: '{skill_name}'. "
                    f"Only alphanumeric characters, hyphens, and underscores allowed"
                )

            return cls(namespace=None, name=skill_name, is_scoped=False)

    def __str__(self) -> str:
        """Return the full skill name string."""
        if self.is_scoped:
            return f"@{self.namespace}/{self.name}"
        return self.name

    def to_filesystem_name(self) -> str:
        """Convert to filesystem-safe directory name."""
        if self.is_scoped:
            return f"{self.namespace}_{self.name}"
        return self.name


def validate_namespace(namespace: str) -> None:
    """Validate a namespace string.

    Args:
        namespace: Namespace to validate

    Raises:
        ValueError: If namespace format is invalid
    """
    if not namespace:
        raise ValueError("Namespace cannot be empty")

    if not re.match(r"^[a-zA-Z0-9_-]+$", namespace):
        raise ValueError(
            f"Invalid namespace: '{namespace}'. "
            f"Only alphanumeric characters, hyphens, and underscores allowed"
        )

    if namespace.startswith("@"):
        raise ValueError(f"Namespace should not start with '@': '{namespace}'")


def validate_skill_name(name: str) -> None:
    """Validate a skill name (without namespace).

    Args:
        name: Skill name to validate

    Raises:
        ValueError: If skill name format is invalid
    """
    if not name:
        raise ValueError("Skill name cannot be empty")

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(
            f"Invalid skill name: '{name}'. "
            f"Only alphanumeric characters, hyphens, and underscores allowed"
        )

    if name.startswith("@") or "/" in name:
        raise ValueError(f"Invalid skill name: '{name}'. Use SkillName.parse() for scoped names")

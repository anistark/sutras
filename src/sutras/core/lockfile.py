"""Lock file management for Sutras.

Handles .sutras.lock files that pin exact versions of dependencies
for reproducible installations.
"""

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LockedSkill(BaseModel):
    """A locked skill entry with exact version and integrity info."""

    name: str = Field(..., description="Full skill name (@namespace/name)")
    version: str = Field(..., description="Exact version installed")
    checksum: str | None = Field(None, description="SHA256 checksum of tarball")
    registry: str | None = Field(None, description="Registry the skill was installed from")
    tarball_url: str | None = Field(None, description="URL the skill was downloaded from")
    dependencies: list[str] = Field(
        default_factory=list, description="Direct dependencies of this skill"
    )


class Lockfile(BaseModel):
    """Lockfile schema for .sutras.lock."""

    version: str = Field("1", description="Lockfile format version")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Timestamp when lockfile was generated",
    )
    skills: dict[str, LockedSkill] = Field(
        default_factory=dict, description="Locked skills indexed by name"
    )


class LockfileManager:
    """Manages .sutras.lock files."""

    LOCKFILE_NAME = ".sutras.lock"

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.lockfile_path = self.project_path / self.LOCKFILE_NAME

    def exists(self) -> bool:
        """Check if lockfile exists."""
        return self.lockfile_path.exists()

    def load(self) -> Lockfile:
        """Load lockfile from disk.

        Returns:
            Lockfile object (empty if file doesn't exist)
        """
        if not self.lockfile_path.exists():
            return Lockfile()

        with open(self.lockfile_path) as f:
            data = yaml.safe_load(f) or {}

        return Lockfile(**data)

    def save(self, lockfile: Lockfile) -> None:
        """Save lockfile to disk.

        Args:
            lockfile: Lockfile to save
        """
        lockfile.generated_at = datetime.now(UTC).isoformat()

        with open(self.lockfile_path, "w") as f:
            yaml.safe_dump(
                lockfile.model_dump(exclude_none=True),
                f,
                sort_keys=False,
                default_flow_style=False,
            )

    def add_skill(
        self,
        name: str,
        version: str,
        checksum: str | None = None,
        registry: str | None = None,
        tarball_url: str | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Add or update a locked skill.

        Args:
            name: Skill name
            version: Exact version
            checksum: SHA256 checksum
            registry: Source registry
            tarball_url: Download URL
            dependencies: Direct dependencies
        """
        lockfile = self.load()
        lockfile.skills[name] = LockedSkill(
            name=name,
            version=version,
            checksum=checksum,
            registry=registry,
            tarball_url=tarball_url,
            dependencies=dependencies or [],
        )
        self.save(lockfile)

    def remove_skill(self, name: str) -> None:
        """Remove a skill from the lockfile.

        Args:
            name: Skill name to remove
        """
        lockfile = self.load()
        if name in lockfile.skills:
            del lockfile.skills[name]
            self.save(lockfile)

    def get_skill(self, name: str) -> LockedSkill | None:
        """Get a locked skill by name.

        Args:
            name: Skill name

        Returns:
            LockedSkill or None if not found
        """
        lockfile = self.load()
        return lockfile.skills.get(name)

    def get_locked_version(self, name: str) -> str | None:
        """Get the locked version for a skill.

        Args:
            name: Skill name

        Returns:
            Locked version string or None
        """
        skill = self.get_skill(name)
        return skill.version if skill else None

    def clear(self) -> None:
        """Clear all locked skills."""
        lockfile = Lockfile()
        self.save(lockfile)

    def delete(self) -> None:
        """Delete the lockfile."""
        if self.lockfile_path.exists():
            self.lockfile_path.unlink()

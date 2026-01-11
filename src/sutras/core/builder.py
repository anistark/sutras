"""Skill packaging and distribution builder."""

import hashlib
import json
import re
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sutras.core.skill import Skill


class BuildError(Exception):
    """Raised when skill build fails."""

    pass


class SkillBuilder:
    """Builds distributable packages from skills."""

    def __init__(self, skill: Skill, output_dir: Path | None = None):
        self.skill = skill
        self.output_dir = output_dir or Path.cwd() / "dist"

    def validate_version(self, version: str) -> bool:
        """Validate semantic version format.

        Args:
            version: Version string to validate

        Returns:
            True if valid semver format

        Raises:
            BuildError: If version is invalid
        """
        semver_pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$"
        if not re.match(semver_pattern, version):
            raise BuildError(
                f"Invalid version '{version}'. Must follow semver format (e.g., 1.0.0, 1.0.0-beta, 1.0.0+build)"
            )
        return True

    def validate_for_distribution(self) -> list[str]:
        """Validate skill is ready for distribution.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.skill.name:
            errors.append("Skill name is required")

        if not self.skill.description:
            errors.append("Skill description is required")

        if not self.skill.abi:
            errors.append("sutras.yaml is required for distribution")
            return errors

        if not self.skill.abi.version:
            errors.append("Version is required in sutras.yaml")
        else:
            try:
                self.validate_version(self.skill.abi.version)
            except BuildError as e:
                errors.append(str(e))

        if not self.skill.abi.author:
            errors.append("Author is required in sutras.yaml")

        if not self.skill.abi.license:
            errors.append("License is required in sutras.yaml")

        return errors

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_manifest(self) -> dict[str, Any]:
        """Create package manifest.

        Returns:
            Manifest dictionary
        """
        manifest = {
            "name": self.skill.name,
            "version": self.skill.abi.version if self.skill.abi else "0.0.0",
            "description": self.skill.description,
            "author": self.skill.abi.author if self.skill.abi else None,
            "license": self.skill.abi.license if self.skill.abi else None,
            "build_timestamp": datetime.now(UTC).isoformat(),
            "files": {},
        }

        if self.skill.abi:
            if self.skill.abi.repository:
                manifest["repository"] = self.skill.abi.repository

            if self.skill.abi.distribution:
                manifest["distribution"] = {
                    "tags": self.skill.abi.distribution.tags,
                    "category": self.skill.abi.distribution.category,
                    "keywords": self.skill.abi.distribution.keywords,
                }

            if self.skill.abi.capabilities and self.skill.abi.capabilities.dependencies:
                manifest["dependencies"] = self.skill.abi.capabilities.dependencies

        return manifest

    def build(self, validate: bool = True) -> Path:
        """Build distributable package.

        Args:
            validate: Whether to validate before building

        Returns:
            Path to created package

        Raises:
            BuildError: If validation fails or build fails
        """
        if validate:
            errors = self.validate_for_distribution()
            if errors:
                raise BuildError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        version = self.skill.abi.version if self.skill.abi else "0.0.0"
        package_name = f"{self.skill.name}-{version}.tar.gz"
        package_path = self.output_dir / package_name

        self.output_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            skill_dir = tmpdir_path / self.skill.name

            skill_dir.mkdir(parents=True, exist_ok=True)

            manifest = self.create_manifest()

            files_to_package = [
                ("SKILL.md", self.skill.path / "SKILL.md"),
            ]

            if (self.skill.path / "sutras.yaml").exists():
                files_to_package.append(("sutras.yaml", self.skill.path / "sutras.yaml"))

            for filename, filepath in self.skill.supporting_files.items():
                files_to_package.append((filename, filepath))

            for dest_name, src_path in files_to_package:
                if src_path.exists():
                    dest_path = skill_dir / dest_name
                    dest_path.write_bytes(src_path.read_bytes())
                    manifest["files"][dest_name] = {
                        "size": src_path.stat().st_size,
                        "checksum": self.calculate_checksum(src_path),
                    }

            manifest_path = skill_dir / "MANIFEST.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))

            with tarfile.open(package_path, "w:gz") as tar:
                tar.add(skill_dir, arcname=self.skill.name)

        return package_path

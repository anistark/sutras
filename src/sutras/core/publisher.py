"""Skill publishing system for Sutras.

Handles publishing skills to registries with support for:
- Direct push to registry (requires write access)
- Pull request workflow (for public registries)
- Automatic index.yaml updates
"""

import shutil
import subprocess
from pathlib import Path

from .builder import SkillBuilder
from .config import SutrasConfig
from .naming import SkillName
from .registry import RegistryManager
from .skill import Skill


class PublishError(Exception):
    """Raised when skill publishing fails."""

    pass


class SkillPublisher:
    """Manages skill publishing to registries."""

    def __init__(self, config: SutrasConfig | None = None):
        self.config = config or SutrasConfig()
        self.registry_manager = RegistryManager(config)

    def _validate_skill_for_publish(self, skill: Skill) -> None:
        """Validate skill is ready for publishing.

        Args:
            skill: Skill to validate

        Raises:
            PublishError: If skill is not valid for publishing
        """
        if not skill.name:
            raise PublishError("Skill name is required")

        try:
            skill_name = SkillName.parse(skill.name)
            if not skill_name.is_scoped:
                raise PublishError(
                    f"Skill name must be scoped for publishing (e.g., @namespace/{skill.name}). "
                    f"Bare names are only for local development."
                )
        except ValueError as e:
            raise PublishError(f"Invalid skill name: {e}")

        if not skill.abi:
            raise PublishError("sutras.yaml is required for publishing")

        builder = SkillBuilder(skill)
        errors = builder.validate_for_distribution()
        if errors:
            raise PublishError("Validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def _prepare_registry(self, registry_name: str, use_pr: bool) -> Path:
        """Prepare registry for publishing.

        Args:
            registry_name: Name of registry to publish to
            use_pr: Whether to use PR workflow

        Returns:
            Path to registry directory

        Raises:
            PublishError: If registry preparation fails
        """
        try:
            registry = self.registry_manager.get_registry(registry_name)
        except ValueError as e:
            raise PublishError(str(e))

        if use_pr:
            try:
                result = subprocess.run(
                    ["git", "-C", str(registry.cache_path), "checkout", "-b", "publish-skill"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    subprocess.run(
                        ["git", "-C", str(registry.cache_path), "checkout", "publish-skill"],
                        check=True,
                    )
            except subprocess.CalledProcessError as e:
                raise PublishError(f"Failed to prepare branch for PR: {e}")

        return registry.cache_path

    def _copy_skill_to_registry(
        self, skill_path: Path, registry_path: Path, skill_name: SkillName
    ) -> Path:
        """Copy skill files to registry.

        Args:
            skill_path: Path to skill directory
            registry_path: Path to registry directory
            skill_name: Parsed skill name

        Returns:
            Path to skill directory in registry
        """
        skills_dir = registry_path / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        full_name = str(skill_name)
        skill_registry_dir = skills_dir / full_name

        if skill_registry_dir.exists():
            shutil.rmtree(skill_registry_dir)

        skill_registry_dir.mkdir(parents=True, exist_ok=True)

        for file in ["SKILL.md", "sutras.yaml"]:
            src = skill_path / file
            if src.exists():
                shutil.copy2(src, skill_registry_dir / file)

        return skill_registry_dir

    def _copy_tarball_to_registry(self, tarball_path: Path, skill_registry_dir: Path) -> None:
        """Copy built tarball to registry.

        Args:
            tarball_path: Path to tarball
            skill_registry_dir: Skill directory in registry
        """
        dest = skill_registry_dir / tarball_path.name
        shutil.copy2(tarball_path, dest)

    def _commit_and_push(
        self,
        registry_path: Path,
        skill_name: SkillName,
        version: str,
        use_pr: bool,
    ) -> None:
        """Commit changes and push to registry.

        Args:
            registry_path: Path to registry directory
            skill_name: Parsed skill name
            version: Skill version
            use_pr: Whether to use PR workflow

        Raises:
            PublishError: If git operations fail
        """
        try:
            subprocess.run(
                ["git", "-C", str(registry_path), "add", "."],
                check=True,
                capture_output=True,
            )

            commit_msg = f"Publish {skill_name} {version}"
            subprocess.run(
                ["git", "-C", str(registry_path), "commit", "-m", commit_msg],
                check=True,
                capture_output=True,
            )

            if use_pr:
                subprocess.run(
                    ["git", "-C", str(registry_path), "push", "-u", "origin", "publish-skill"],
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["git", "-C", str(registry_path), "push"],
                    check=True,
                    capture_output=True,
                )

        except subprocess.CalledProcessError as e:
            raise PublishError(f"Git operation failed: {e.stderr.decode().strip()}")

    def publish(
        self,
        skill_path: Path,
        registry_name: str | None = None,
        use_pr: bool = False,
        build_dir: Path | None = None,
    ) -> None:
        """Publish a skill to a registry.

        Args:
            skill_path: Path to skill directory
            registry_name: Registry to publish to (default: default registry)
            use_pr: Use pull request workflow instead of direct push
            build_dir: Optional custom build directory

        Raises:
            PublishError: If publishing fails
        """
        skill = Skill.load(skill_path)
        self._validate_skill_for_publish(skill)

        skill_name = SkillName.parse(skill.name)

        if registry_name is None:
            registry_name = self.config.config.default_registry
            if not registry_name:
                raise PublishError(
                    "No default registry configured. "
                    "Use --registry flag or configure a default registry."
                )

        print(f"Building {skill_name}...")
        builder = SkillBuilder(skill, output_dir=build_dir or Path.cwd() / "dist")
        tarball_path = builder.build()

        version = skill.abi.version if skill.abi else "0.0.0"

        print(f"Preparing registry '{registry_name}'...")
        registry_path = self._prepare_registry(registry_name, use_pr)

        print("Copying skill to registry...")
        skill_registry_dir = self._copy_skill_to_registry(skill_path, registry_path, skill_name)

        print("Copying tarball...")
        self._copy_tarball_to_registry(tarball_path, skill_registry_dir)

        print("Updating index...")
        self.registry_manager.build_index(registry_path)

        if use_pr:
            print("Committing and pushing for PR...")
            self._commit_and_push(registry_path, skill_name, version, use_pr)
            print("\n✓ Changes pushed to branch 'publish-skill'")
            print("Create a pull request to complete publishing")
        else:
            print("Committing and pushing...")
            self._commit_and_push(registry_path, skill_name, version, use_pr)
            print(f"\n✓ Published {skill_name} {version} to {registry_name}")

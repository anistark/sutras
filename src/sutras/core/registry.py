"""Registry management for Sutras.

Handles federated Git-based skill registries including:
- Registry index parsing (index.yaml)
- Registry metadata (registry.yaml)
- Multi-registry management
- Git-based caching
"""

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .config import SutrasConfig
from .naming import SkillName


class SkillIndexEntry(BaseModel):
    """A single skill entry in the registry index."""

    name: str = Field(..., description="Skill name with namespace (@namespace/name)")
    version: str = Field(..., description="Latest version")
    description: str | None = Field(None, description="Short description")
    author: str | None = Field(None, description="Skill author")
    homepage: str | None = Field(None, description="Homepage URL")
    tarball_url: str | None = Field(None, description="Download URL for tarball")
    checksum: str | None = Field(None, description="SHA256 checksum")
    versions: dict[str, str] = Field(
        default_factory=dict, description="Available versions (version -> tarball_url)"
    )


class RegistryMetadata(BaseModel):
    """Registry metadata from registry.yaml."""

    name: str = Field(..., description="Registry name")
    description: str | None = Field(None, description="Registry description")
    homepage: str | None = Field(None, description="Registry homepage")
    visibility: str = Field("public", description="public or private")
    maintainers: list[str] = Field(default_factory=list, description="Registry maintainers")


class RegistryIndex(BaseModel):
    """Parsed registry index from index.yaml."""

    version: str = Field("1.0", description="Index format version")
    skills: dict[str, SkillIndexEntry] = Field(
        default_factory=dict, description="Skills indexed by full name"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@dataclass
class CachedRegistry:
    """A cached registry with its index."""

    name: str
    url: str
    cache_path: Path
    index: RegistryIndex
    metadata: RegistryMetadata | None = None


class RegistryManager:
    """Manages multiple skill registries."""

    def __init__(self, config: SutrasConfig | None = None):
        self.config = config or SutrasConfig()
        self.cache_dir = self.config.get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cached_registries: dict[str, CachedRegistry] = {}

    def _get_registry_cache_path(self, name: str) -> Path:
        """Get the cache path for a registry."""
        safe_name = name.replace("/", "_").replace(":", "_")
        return self.cache_dir / safe_name

    def _clone_or_update_registry(self, name: str, url: str, cache_path: Path) -> None:
        """Clone or update a registry repository."""
        if cache_path.exists():
            try:
                subprocess.run(
                    ["git", "-C", str(cache_path), "pull", "--quiet"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to update registry '{name}': {e.stderr.decode().strip()}"
                )
        else:
            try:
                subprocess.run(
                    ["git", "clone", "--quiet", url, str(cache_path)],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to clone registry '{name}': {e.stderr.decode().strip()}"
                )

    def _load_registry_index(self, cache_path: Path) -> RegistryIndex:
        """Load registry index from cache."""
        index_path = cache_path / "index.yaml"
        if not index_path.exists():
            return RegistryIndex()

        with open(index_path) as f:
            data = yaml.safe_load(f) or {}

        return RegistryIndex(**data)

    def _load_registry_metadata(self, cache_path: Path) -> RegistryMetadata | None:
        """Load registry metadata from cache."""
        metadata_path = cache_path / "registry.yaml"
        if not metadata_path.exists():
            return None

        with open(metadata_path) as f:
            data = yaml.safe_load(f) or {}

        return RegistryMetadata(**data)

    def update_registry(self, name: str) -> CachedRegistry:
        """Update a registry's cached index."""
        registry_config = self.config.get_registry(name)
        cache_path = self._get_registry_cache_path(name)

        self._clone_or_update_registry(name, registry_config.url, cache_path)

        index = self._load_registry_index(cache_path)
        metadata = self._load_registry_metadata(cache_path)

        cached = CachedRegistry(
            name=name,
            url=registry_config.url,
            cache_path=cache_path,
            index=index,
            metadata=metadata,
        )

        self._cached_registries[name] = cached
        return cached

    def update_all_registries(self) -> None:
        """Update all configured registries."""
        for name in self.config.list_registries():
            try:
                self.update_registry(name)
            except Exception as e:
                print(f"Warning: Failed to update registry '{name}': {e}")

    def get_registry(self, name: str) -> CachedRegistry:
        """Get a cached registry, loading it if necessary."""
        if name in self._cached_registries:
            return self._cached_registries[name]

        registry_config = self.config.get_registry(name)
        cache_path = self._get_registry_cache_path(name)

        if not cache_path.exists():
            self._clone_or_update_registry(name, registry_config.url, cache_path)

        index = self._load_registry_index(cache_path)
        metadata = self._load_registry_metadata(cache_path)

        cached = CachedRegistry(
            name=name,
            url=registry_config.url,
            cache_path=cache_path,
            index=index,
            metadata=metadata,
        )

        self._cached_registries[name] = cached
        return cached

    def search_skill(self, skill_name: str | SkillName) -> list[tuple[str, SkillIndexEntry]]:
        """Search for a skill across all registries.

        Args:
            skill_name: Skill name to search for

        Returns:
            List of (registry_name, entry) tuples for matching skills
        """
        if isinstance(skill_name, str):
            skill_name = SkillName.parse(skill_name)

        full_name = str(skill_name)
        results = []

        registries = sorted(
            self.config.list_registries().items(),
            key=lambda x: x[1].priority,
            reverse=True,
        )

        for reg_name, reg_config in registries:
            if not reg_config.enabled:
                continue

            try:
                cached = self.get_registry(reg_name)
                if full_name in cached.index.skills:
                    results.append((reg_name, cached.index.skills[full_name]))
            except Exception:
                continue

        return results

    def find_skill(self, skill_name: str | SkillName) -> tuple[str, SkillIndexEntry]:
        """Find a skill in registries (highest priority first).

        Args:
            skill_name: Skill name to find

        Returns:
            Tuple of (registry_name, entry)

        Raises:
            ValueError: If skill not found in any registry
        """
        results = self.search_skill(skill_name)
        if not results:
            raise ValueError(f"Skill '{skill_name}' not found in any configured registry")

        return results[0]

    def build_index(self, registry_path: Path, output_path: Path | None = None) -> None:
        """Build index.yaml for a local registry.

        Args:
            registry_path: Path to registry directory
            output_path: Optional output path for index.yaml
        """
        output_path = output_path or registry_path / "index.yaml"

        skills_dir = registry_path / "skills"
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)

        skills = {}

        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            sutras_yaml = skill_dir / "sutras.yaml"
            if not sutras_yaml.exists():
                continue

            with open(sutras_yaml) as f:
                skill_data = yaml.safe_load(f) or {}

            skill_name = skill_dir.name
            version = skill_data.get("version", "0.0.0")
            author = skill_data.get("author")
            description = skill_data.get("description")
            homepage = skill_data.get("distribution", {}).get("homepage")

            tarball_path = skill_dir / f"{skill_dir.name}-{version}.tar.gz"
            tarball_url = None
            checksum = None

            if tarball_path.exists():
                with open(tarball_path, "rb") as f:
                    checksum = hashlib.sha256(f.read()).hexdigest()
                tarball_url = f"skills/{skill_dir.name}/{tarball_path.name}"

            skills[skill_name] = SkillIndexEntry(
                name=skill_name,
                version=version,
                description=description,
                author=author,
                homepage=homepage,
                tarball_url=tarball_url,
                checksum=checksum,
                versions={version: tarball_url} if tarball_url else {},
            )

        index = RegistryIndex(skills=skills)

        with open(output_path, "w") as f:
            yaml.safe_dump(index.model_dump(exclude_none=True), f, sort_keys=False)

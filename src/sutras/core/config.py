"""Configuration management for Sutras.

Handles global configuration stored in ~/.sutras/config.yaml including
registry configuration, authentication, and user preferences.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RegistryConfigEntry(BaseModel):
    """Configuration for a single registry."""

    url: str = Field(..., description="Git URL of the registry")
    namespace: str | None = Field(None, description="Default namespace for this registry")
    auth_token: str | None = Field(None, description="Authentication token")
    priority: int = Field(0, description="Registry priority (higher = checked first)")
    enabled: bool = Field(True, description="Whether this registry is enabled")


class GlobalConfig(BaseModel):
    """Global Sutras configuration."""

    registries: dict[str, RegistryConfigEntry] = Field(
        default_factory=dict, description="Configured registries"
    )
    default_registry: str | None = Field(None, description="Default registry for publishing")
    cache_dir: str | None = Field(None, description="Custom cache directory")
    skills_dir: str | None = Field(None, description="Custom skills installation directory")


class SutrasConfig:
    """Manages global Sutras configuration."""

    DEFAULT_CONFIG_DIR = Path.home() / ".sutras"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
    DEFAULT_CACHE_DIR = DEFAULT_CONFIG_DIR / "registry-cache"
    DEFAULT_INSTALLED_DIR = Path.home() / ".claude" / "installed"
    DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills"

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self._config: GlobalConfig | None = None

    @property
    def config(self) -> GlobalConfig:
        if self._config is None:
            self._config = self.load()
        return self._config

    def load(self) -> GlobalConfig:
        """Load configuration from disk."""
        if not self.config_path.exists():
            self._config = GlobalConfig()
            return self._config

        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}

        self._config = GlobalConfig(**data)
        return self._config

    def save(self) -> None:
        """Save configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config.model_dump(exclude_none=True), f, sort_keys=False)

    def add_registry(
        self,
        name: str,
        url: str,
        namespace: str | None = None,
        auth_token: str | None = None,
        priority: int = 0,
        set_default: bool = False,
    ) -> None:
        """Add or update a registry configuration."""
        self.config.registries[name] = RegistryConfigEntry(
            url=url, namespace=namespace, auth_token=auth_token, priority=priority
        )

        if set_default or self.config.default_registry is None:
            self.config.default_registry = name

        self.save()

    def remove_registry(self, name: str) -> None:
        """Remove a registry configuration."""
        if name not in self.config.registries:
            raise ValueError(f"Registry '{name}' not found")

        del self.config.registries[name]

        if self.config.default_registry == name:
            self.config.default_registry = (
                next(iter(self.config.registries.keys()), None) if self.config.registries else None
            )

        self.save()

    def get_registry(self, name: str) -> RegistryConfigEntry:
        """Get a registry configuration by name."""
        if name not in self.config.registries:
            raise ValueError(f"Registry '{name}' not found")
        return self.config.registries[name]

    def list_registries(self) -> dict[str, RegistryConfigEntry]:
        """List all configured registries."""
        return self.config.registries

    def get_cache_dir(self) -> Path:
        """Get the registry cache directory."""
        if self.config.cache_dir:
            return Path(self.config.cache_dir)
        return self.DEFAULT_CACHE_DIR

    def get_installed_dir(self) -> Path:
        """Get the installed skills directory."""
        if self.config.skills_dir:
            return Path(self.config.skills_dir) / "installed"
        return self.DEFAULT_INSTALLED_DIR

    def get_skills_dir(self) -> Path:
        """Get the skills symlink directory."""
        if self.config.skills_dir:
            return Path(self.config.skills_dir)
        return self.DEFAULT_SKILLS_DIR

"""Tests for configuration management."""

import pytest
import yaml

from sutras.core.config import GlobalConfig, RegistryConfigEntry, SutrasConfig


class TestRegistryConfigEntry:
    def test_create_minimal(self):
        entry = RegistryConfigEntry(url="https://github.com/user/repo")
        assert entry.url == "https://github.com/user/repo"
        assert entry.namespace is None
        assert entry.auth_token is None
        assert entry.priority == 0
        assert entry.enabled is True

    def test_create_full(self):
        entry = RegistryConfigEntry(
            url="https://github.com/user/repo",
            namespace="user",
            auth_token="secret",
            priority=10,
            enabled=False,
        )
        assert entry.url == "https://github.com/user/repo"
        assert entry.namespace == "user"
        assert entry.auth_token == "secret"
        assert entry.priority == 10
        assert entry.enabled is False


class TestGlobalConfig:
    def test_empty_config(self):
        config = GlobalConfig()
        assert config.registries == {}
        assert config.default_registry is None
        assert config.cache_dir is None
        assert config.skills_dir is None

    def test_with_registries(self):
        config = GlobalConfig(
            registries={
                "official": RegistryConfigEntry(url="https://example.com/registry"),
            },
            default_registry="official",
        )
        assert "official" in config.registries
        assert config.default_registry == "official"


class TestSutrasConfig:
    def test_load_nonexistent(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        loaded = config.load()
        assert loaded.registries == {}

    def test_load_existing(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_data = {
            "registries": {
                "test": {
                    "url": "https://example.com",
                    "priority": 5,
                }
            },
            "default_registry": "test",
        }
        with open(config_path, "w") as f:
            yaml.safe_dump(config_data, f)

        config = SutrasConfig(config_path=config_path)
        loaded = config.load()
        assert "test" in loaded.registries
        assert loaded.registries["test"].url == "https://example.com"
        assert loaded.registries["test"].priority == 5
        assert loaded.default_registry == "test"

    def test_save(self, tmp_path):
        config_path = tmp_path / "sutras" / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        config.config.registries["new"] = RegistryConfigEntry(url="https://new.com")
        config.save()

        assert config_path.exists()
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert "new" in data["registries"]

    def test_add_registry(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        config.add_registry(
            name="test",
            url="https://example.com",
            namespace="user",
            priority=10,
        )

        assert "test" in config.config.registries
        assert config.config.registries["test"].url == "https://example.com"
        assert config.config.registries["test"].namespace == "user"
        assert config.config.registries["test"].priority == 10

    def test_add_registry_sets_default(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        config.add_registry(name="first", url="https://first.com")
        assert config.config.default_registry == "first"

        config.add_registry(name="second", url="https://second.com")
        assert config.config.default_registry == "first"

        config.add_registry(name="third", url="https://third.com", set_default=True)
        assert config.config.default_registry == "third"

    def test_remove_registry(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        config.add_registry(name="test", url="https://test.com")
        config.add_registry(name="other", url="https://other.com")

        config.remove_registry("test")
        assert "test" not in config.config.registries
        assert "other" in config.config.registries

    def test_remove_registry_updates_default(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        config.add_registry(name="first", url="https://first.com", set_default=True)
        config.add_registry(name="second", url="https://second.com")

        config.remove_registry("first")
        assert config.config.default_registry == "second"

    def test_remove_nonexistent_raises(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        with pytest.raises(ValueError, match="not found"):
            config.remove_registry("nonexistent")

    def test_get_registry(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        config.add_registry(name="test", url="https://test.com")

        entry = config.get_registry("test")
        assert entry.url == "https://test.com"

    def test_get_registry_nonexistent_raises(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)

        with pytest.raises(ValueError, match="not found"):
            config.get_registry("nonexistent")

    def test_list_registries(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        config.add_registry(name="a", url="https://a.com")
        config.add_registry(name="b", url="https://b.com")

        registries = config.list_registries()
        assert len(registries) == 2
        assert "a" in registries
        assert "b" in registries

    def test_get_cache_dir_default(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        cache_dir = config.get_cache_dir()
        assert "registry-cache" in str(cache_dir)

    def test_get_cache_dir_custom(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        config.config.cache_dir = "/custom/cache"
        assert str(config.get_cache_dir()) == "/custom/cache"

    def test_get_skills_dir_default(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        skills_dir = config.get_skills_dir()
        assert "skills" in str(skills_dir)

    def test_get_installed_dir_default(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config = SutrasConfig(config_path=config_path)
        installed_dir = config.get_installed_dir()
        assert "installed" in str(installed_dir)

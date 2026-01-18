"""Skill installation system for Sutras.

Handles installing skills from multiple sources:
- Registries: @namespace/skill-name
- URLs: https://example.com/skill.tar.gz
- GitHub releases: github:user/repo@version
- Local files: ./skill.tar.gz or /path/to/skill.tar.gz
"""

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

import yaml

from .config import SutrasConfig
from .naming import SkillName
from .registry import RegistryManager


class SkillInstaller:
    """Manages skill installation and uninstallation."""

    def __init__(self, config: SutrasConfig | None = None):
        self.config = config or SutrasConfig()
        self.installed_dir = self.config.get_installed_dir()
        self.skills_dir = self.config.get_skills_dir()
        self.registry_manager = RegistryManager(config)

        self.installed_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def _download_and_verify(self, url: str, expected_checksum: str | None) -> Path:
        """Download a tarball and verify its checksum.

        Args:
            url: URL to download
            expected_checksum: Expected SHA256 checksum

        Returns:
            Path to downloaded file

        Raises:
            ValueError: If checksum doesn't match
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as f:
            temp_path = Path(f.name)

            with urlopen(url) as response:
                f.write(response.read())

        if expected_checksum:
            with open(temp_path, "rb") as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()

            if actual_checksum != expected_checksum:
                temp_path.unlink()
                raise ValueError(
                    f"Checksum mismatch for {url}. "
                    f"Expected: {expected_checksum}, Got: {actual_checksum}"
                )

        return temp_path

    def _extract_tarball(self, tarball_path: Path, dest_dir: Path) -> None:
        """Extract a tarball to destination directory.

        Args:
            tarball_path: Path to tarball
            dest_dir: Destination directory
        """
        dest_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(dest_dir)

    def _create_symlink(self, skill_name: SkillName, install_path: Path) -> None:
        """Create or update symlink in skills directory.

        Args:
            skill_name: Skill name
            install_path: Path to installed skill
        """
        symlink_path = self.skills_dir / skill_name.name

        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

        symlink_path.symlink_to(install_path)

    def _remove_symlink(self, skill_name: SkillName) -> None:
        """Remove symlink from skills directory.

        Args:
            skill_name: Skill name
        """
        symlink_path = self.skills_dir / skill_name.name

        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

    def _read_skill_metadata_from_tarball(self, tarball_path: Path) -> tuple[str, str]:
        """Extract skill name and version from tarball.

        Args:
            tarball_path: Path to tarball

        Returns:
            Tuple of (skill_name, version)

        Raises:
            ValueError: If metadata cannot be read
        """
        with tarfile.open(tarball_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("/sutras.yaml") or member.name == "sutras.yaml":
                    f = tar.extractfile(member)
                    if f:
                        data = yaml.safe_load(f.read())
                        version = data.get("version", "0.0.0")

                        skill_name = None
                        for m in tar.getmembers():
                            if m.name.endswith("/SKILL.md") or m.name == "SKILL.md":
                                skill_f = tar.extractfile(m)
                                if skill_f:
                                    content = skill_f.read().decode("utf-8")
                                    match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
                                    if match:
                                        skill_name = match.group(1).strip()
                                    break

                        if not skill_name:
                            parts = member.name.split("/")
                            if len(parts) > 1:
                                skill_name = parts[0]
                            else:
                                raise ValueError("Could not determine skill name from tarball")

                        return skill_name, version

        raise ValueError("No sutras.yaml found in tarball")

    def _resolve_github_release_url(self, github_spec: str) -> tuple[str, str, str]:
        """Resolve GitHub release spec to download URL.

        Args:
            github_spec: Format "github:user/repo@version" or "github:user/repo"

        Returns:
            Tuple of (download_url, skill_name, version)

        Raises:
            ValueError: If spec format is invalid or release not found
        """
        if not github_spec.startswith("github:"):
            raise ValueError(f"Invalid GitHub spec: {github_spec}")

        spec = github_spec[7:]
        match = re.match(r"^([^/]+)/([^@]+)(?:@(.+))?$", spec)
        if not match:
            raise ValueError(
                f"Invalid GitHub spec format: {github_spec}. "
                f"Expected: github:user/repo@version or github:user/repo"
            )

        user, repo, version = match.groups()

        if version:
            tag = version if version.startswith("v") else f"v{version}"
        else:
            tag = "latest"

        api_url = f"https://api.github.com/repos/{user}/{repo}/releases/{tag}"

        try:
            with urlopen(api_url) as response:
                release_data = json.loads(response.read())
        except Exception as e:
            raise ValueError(f"Failed to fetch GitHub release for {user}/{repo}@{tag}: {e}")

        if "assets" not in release_data or not release_data["assets"]:
            raise ValueError(
                f"No assets found in GitHub release {user}/{repo}@{tag}. "
                f"Make sure the release has a .tar.gz file attached."
            )

        for asset in release_data["assets"]:
            if asset["name"].endswith(".tar.gz"):
                download_url = asset["browser_download_url"]
                actual_version = release_data.get("tag_name", "").lstrip("v")

                asset_name = asset["name"].replace(".tar.gz", "")
                parts = asset_name.rsplit("-", 1)
                skill_name = parts[0] if len(parts) > 1 else asset_name

                return download_url, skill_name, actual_version

        raise ValueError(f"No .tar.gz asset found in GitHub release {user}/{repo}@{tag}")

    def _detect_install_source(self, source: str) -> str:
        """Detect the type of installation source.

        Args:
            source: Installation source string

        Returns:
            One of: "registry", "url", "github", "file"
        """
        if source.startswith("github:"):
            return "github"
        elif source.startswith(("http://", "https://")):
            return "url"
        elif Path(source).exists():
            return "file"
        elif source.startswith("@"):
            return "registry"
        else:
            return "registry"

    def install(
        self,
        source: str | SkillName,
        version: str | None = None,
        registry_name: str | None = None,
    ) -> Path:
        """Install a skill from various sources.

        Args:
            source: Installation source:
                - Registry: @namespace/skill-name
                - URL: https://example.com/skill.tar.gz
                - GitHub: github:user/repo@version
                - Local file: ./skill.tar.gz or /path/to/skill.tar.gz
            version: Specific version (only for registry installs)
            registry_name: Registry to install from (only for registry installs)

        Returns:
            Path to installed skill

        Raises:
            ValueError: If installation fails
        """
        source_str = str(source)
        source_type = self._detect_install_source(source_str)

        if source_type == "registry":
            return self._install_from_registry(source, version, registry_name)
        elif source_type == "github":
            return self._install_from_github(source_str)
        elif source_type == "url":
            return self._install_from_url(source_str)
        elif source_type == "file":
            return self._install_from_file(Path(source_str))
        else:
            raise ValueError(f"Unknown installation source type: {source_type}")

    def _install_from_registry(
        self,
        skill_name: str | SkillName,
        version: str | None = None,
        registry_name: str | None = None,
    ) -> Path:
        """Install a skill from a registry.

        Args:
            skill_name: Skill name to install
            version: Specific version to install (default: latest)
            registry_name: Registry to install from (default: search all)

        Returns:
            Path to installed skill

        Raises:
            ValueError: If skill not found or version not available
        """
        if isinstance(skill_name, str):
            skill_name = SkillName.parse(skill_name)

        if not skill_name.is_scoped:
            raise ValueError(
                f"Cannot install bare skill name '{skill_name}'. "
                f"Use scoped names (@namespace/name) for registry skills."
            )

        if registry_name:
            registry = self.registry_manager.get_registry(registry_name)
            full_name = str(skill_name)
            if full_name not in registry.index.skills:
                raise ValueError(f"Skill '{skill_name}' not found in registry '{registry_name}'")
            entry = registry.index.skills[full_name]
        else:
            registry_name, entry = self.registry_manager.find_skill(skill_name)

        if version is None:
            version = entry.version
            tarball_url = entry.tarball_url
            checksum = entry.checksum
        else:
            if version not in entry.versions:
                raise ValueError(
                    f"Version {version} not available for '{skill_name}'. "
                    f"Available: {list(entry.versions.keys())}"
                )
            tarball_url = entry.versions[version]
            checksum = None

        if not tarball_url:
            raise ValueError(f"No tarball URL available for '{skill_name}' version {version}")

        registry = self.registry_manager.get_registry(registry_name)
        if not tarball_url.startswith(("http://", "https://")):
            tarball_url = f"{registry.url}/raw/main/{tarball_url}"

        print(f"Downloading {skill_name} {version} from {registry_name}...")
        tarball_path = self._download_and_verify(tarball_url, checksum)

        install_dir = self.installed_dir / skill_name.to_filesystem_name() / version
        if install_dir.exists():
            shutil.rmtree(install_dir)

        print(f"Installing to {install_dir}...")
        self._extract_tarball(tarball_path, install_dir)
        tarball_path.unlink()

        self._create_symlink(skill_name, install_dir)

        print(f"✓ Installed {skill_name} {version}")
        return install_dir

    def _install_from_url(self, url: str) -> Path:
        """Install a skill from a direct URL.

        Args:
            url: HTTPS URL to skill tarball

        Returns:
            Path to installed skill
        """
        print(f"Downloading from {url}...")
        tarball_path = self._download_and_verify(url, None)

        try:
            skill_name_str, version = self._read_skill_metadata_from_tarball(tarball_path)
            skill_name = SkillName.parse(skill_name_str)

            install_dir = self.installed_dir / skill_name.to_filesystem_name() / version
            if install_dir.exists():
                shutil.rmtree(install_dir)

            print(f"Installing {skill_name} {version}...")
            self._extract_tarball(tarball_path, install_dir)
            self._create_symlink(skill_name, install_dir)

            print(f"✓ Installed {skill_name} {version} from URL")
            return install_dir
        finally:
            tarball_path.unlink()

    def _install_from_github(self, github_spec: str) -> Path:
        """Install a skill from a GitHub release.

        Args:
            github_spec: Format "github:user/repo@version" or "github:user/repo"

        Returns:
            Path to installed skill
        """
        print(f"Resolving GitHub release: {github_spec}...")
        download_url, skill_name_str, version = self._resolve_github_release_url(github_spec)

        print("Downloading from GitHub...")
        tarball_path = self._download_and_verify(download_url, None)

        try:
            actual_skill_name, actual_version = self._read_skill_metadata_from_tarball(tarball_path)
            skill_name = SkillName.parse(actual_skill_name)

            version_to_use = actual_version if actual_version else version

            install_dir = self.installed_dir / skill_name.to_filesystem_name() / version_to_use
            if install_dir.exists():
                shutil.rmtree(install_dir)

            print(f"Installing {skill_name} {version_to_use}...")
            self._extract_tarball(tarball_path, install_dir)
            self._create_symlink(skill_name, install_dir)

            print(f"✓ Installed {skill_name} {version_to_use} from GitHub")
            return install_dir
        finally:
            tarball_path.unlink()

    def _install_from_file(self, file_path: Path) -> Path:
        """Install a skill from a local tarball file.

        Args:
            file_path: Path to local tarball

        Returns:
            Path to installed skill
        """
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        if not file_path.name.endswith(".tar.gz"):
            raise ValueError(f"File must be a .tar.gz tarball: {file_path}")

        print(f"Installing from {file_path}...")
        skill_name_str, version = self._read_skill_metadata_from_tarball(file_path)
        skill_name = SkillName.parse(skill_name_str)

        install_dir = self.installed_dir / skill_name.to_filesystem_name() / version
        if install_dir.exists():
            shutil.rmtree(install_dir)

        print(f"Installing {skill_name} {version}...")
        self._extract_tarball(file_path, install_dir)
        self._create_symlink(skill_name, install_dir)

        print(f"✓ Installed {skill_name} {version} from local file")
        return install_dir

    def uninstall(self, skill_name: str | SkillName, version: str | None = None) -> None:
        """Uninstall a skill.

        Args:
            skill_name: Skill name to uninstall
            version: Specific version to uninstall (default: all versions)
        """
        if isinstance(skill_name, str):
            skill_name = SkillName.parse(skill_name)

        skill_install_dir = self.installed_dir / skill_name.to_filesystem_name()

        if not skill_install_dir.exists():
            raise ValueError(f"Skill '{skill_name}' is not installed")

        if version:
            version_dir = skill_install_dir / version
            if not version_dir.exists():
                raise ValueError(f"Version {version} of '{skill_name}' is not installed")

            print(f"Uninstalling {skill_name} {version}...")
            shutil.rmtree(version_dir)

            remaining_versions = [
                d for d in skill_install_dir.iterdir() if d.is_dir() and d.name != version
            ]
            if not remaining_versions:
                self._remove_symlink(skill_name)
                skill_install_dir.rmdir()
        else:
            print(f"Uninstalling {skill_name}...")
            shutil.rmtree(skill_install_dir)
            self._remove_symlink(skill_name)

        print(f"✓ Uninstalled {skill_name}")

    def list_installed(self) -> dict[str, list[str]]:
        """List all installed skills.

        Returns:
            Dict mapping skill names to list of installed versions
        """
        if not self.installed_dir.exists():
            return {}

        installed = {}
        for skill_dir in self.installed_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            versions = [v.name for v in skill_dir.iterdir() if v.is_dir()]
            if versions:
                installed[skill_dir.name] = sorted(versions)

        return installed

"""Self-update logic for the Sutras CLI.

Handles checking PyPI for the latest version, upgrading the Python CLI
via pipx/uv/pip, updating the pi extension, and refreshing the global skill.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from sutras import __version__
from sutras.core.semver import Version

PYPI_URL = "https://pypi.org/pypi/sutras/json"
NPM_REGISTRY_URL = "https://registry.npmjs.org/sutras"
PI_PACKAGE_NAME = "sutras"


@dataclass
class UpdateResult:
    """Result of an update operation."""

    component: str
    old_version: str | None
    new_version: str | None
    updated: bool
    skipped: bool = False
    error: str | None = None


@dataclass
class UpdateSummary:
    """Summary of all update operations."""

    results: list[UpdateResult] = field(default_factory=list)

    @property
    def any_updated(self) -> bool:
        return any(r.updated for r in self.results)

    @property
    def any_errors(self) -> bool:
        return any(r.error for r in self.results)


def _fetch_json(url: str, timeout: int = 10) -> dict:
    """Fetch JSON from a URL."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing output."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _detect_installer() -> str | None:
    """Detect how sutras was installed (pipx, uv, or pip)."""
    # Check pipx first
    if shutil.which("pipx"):
        result = _run(["pipx", "list", "--short"])
        if result.returncode == 0 and "sutras" in result.stdout:
            return "pipx"

    # Check uv tool
    if shutil.which("uv"):
        result = _run(["uv", "tool", "list"])
        if result.returncode == 0 and "sutras" in result.stdout:
            return "uv"

    # Fallback to pip
    for pip_cmd in ("pip3", "pip"):
        if shutil.which(pip_cmd):
            return pip_cmd

    return None


def fetch_latest_pypi_version() -> str | None:
    """Fetch the latest version of sutras from PyPI.

    Returns:
        Latest version string, or None if the check fails.
    """
    try:
        data = _fetch_json(PYPI_URL)
        return data.get("info", {}).get("version")
    except Exception:
        return None


def fetch_latest_npm_version() -> str | None:
    """Fetch the latest version of the sutras pi extension from npm.

    Returns:
        Latest version string, or None if the check fails.
    """
    try:
        data = _fetch_json(NPM_REGISTRY_URL)
        return data.get("dist-tags", {}).get("latest")
    except Exception:
        return None


def check_update_available() -> tuple[str, str | None]:
    """Check if an update is available.

    Returns:
        Tuple of (current_version, latest_version_or_None).
        latest is None if we can't determine it, or if already up-to-date.
    """
    current = __version__
    latest = fetch_latest_pypi_version()

    if not latest:
        return current, None

    try:
        cur = Version.parse(current)
        lat = Version.parse(latest)
        if lat > cur:
            return current, latest
    except ValueError:
        pass

    return current, None


def upgrade_cli(target_version: str | None = None) -> UpdateResult:
    """Upgrade the sutras Python CLI.

    Args:
        target_version: Specific version to install, or None for latest.

    Returns:
        UpdateResult with outcome details.
    """
    old_version = __version__
    installer = _detect_installer()

    if not installer:
        return UpdateResult(
            component="cli",
            old_version=old_version,
            new_version=None,
            updated=False,
            error="No suitable installer found (need pipx, uv, or pip)",
        )

    spec = f"sutras=={target_version}" if target_version else "sutras"

    try:
        if installer == "pipx":
            if target_version:
                result = _run(["pipx", "install", "--force", f"sutras=={target_version}"])
            else:
                result = _run(["pipx", "upgrade", "sutras"])
                # If upgrade says "already latest" but didn't fail, still ok
                if result.returncode != 0:
                    # Try force reinstall
                    result = _run(["pipx", "install", "--force", "sutras"])

        elif installer == "uv":
            if target_version:
                result = _run(["uv", "tool", "install", "--force", f"sutras=={target_version}"])
            else:
                result = _run(["uv", "tool", "upgrade", "sutras"])
                if result.returncode != 0:
                    result = _run(["uv", "tool", "install", "--force", "sutras"])

        else:  # pip/pip3
            cmd = [installer, "install", "--upgrade"]
            if installer in ("pip3", "pip"):
                cmd.append("--user")
            cmd.append(spec)
            result = _run(cmd)
            if result.returncode != 0:
                # Try with --break-system-packages
                cmd.append("--break-system-packages")
                result = _run(cmd)

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return UpdateResult(
                component="cli",
                old_version=old_version,
                new_version=None,
                updated=False,
                error=f"{installer} upgrade failed: {error_msg}",
            )

        # Determine the new version from the fresh binary
        ver_result = _run(["sutras", "--version"])
        new_version = None
        if ver_result.returncode == 0:
            # Parse "sutras, version X.Y.Z"
            out = ver_result.stdout.strip()
            if "version" in out:
                new_version = out.split("version")[-1].strip()
            else:
                new_version = out.strip()

        actually_updated = new_version != old_version if new_version else True

        return UpdateResult(
            component="cli",
            old_version=old_version,
            new_version=new_version or target_version,
            updated=actually_updated,
            skipped=not actually_updated,
        )

    except subprocess.TimeoutExpired:
        return UpdateResult(
            component="cli",
            old_version=old_version,
            new_version=None,
            updated=False,
            error="Upgrade timed out",
        )
    except Exception as e:
        return UpdateResult(
            component="cli",
            old_version=old_version,
            new_version=None,
            updated=False,
            error=str(e),
        )


def upgrade_pi_extension() -> UpdateResult:
    """Upgrade the sutras pi extension (npm package).

    Tries `pi pkg update` first, then falls back to pnpm/npm.

    Returns:
        UpdateResult with outcome details.
    """
    # Try to get current npm version
    old_version: str | None = None
    try:
        result = _run(["npm", "list", "-g", "sutras", "--json", "--depth=0"])
        if result.returncode == 0:
            data = json.loads(result.stdout)
            old_version = data.get("dependencies", {}).get("sutras", {}).get("version")
    except Exception:
        pass

    # 1) Try pi CLI (preferred)
    if shutil.which("pi"):
        try:
            result = _run(["pi", "pkg", "update", PI_PACKAGE_NAME])
            if result.returncode == 0:
                return UpdateResult(
                    component="pi-extension",
                    old_version=old_version,
                    new_version=fetch_latest_npm_version(),
                    updated=True,
                )
        except Exception:
            pass

    # 2) Try pnpm
    if shutil.which("pnpm"):
        try:
            result = _run(["pnpm", "update", "-g", PI_PACKAGE_NAME])
            if result.returncode == 0:
                return UpdateResult(
                    component="pi-extension",
                    old_version=old_version,
                    new_version=fetch_latest_npm_version(),
                    updated=True,
                )
        except Exception:
            pass

    # 3) Try npm
    if shutil.which("npm"):
        try:
            result = _run(["npm", "update", "-g", PI_PACKAGE_NAME])
            if result.returncode == 0:
                return UpdateResult(
                    component="pi-extension",
                    old_version=old_version,
                    new_version=fetch_latest_npm_version(),
                    updated=True,
                )
        except Exception:
            pass

    # Not a hard error — pi extension is optional
    return UpdateResult(
        component="pi-extension",
        old_version=old_version,
        new_version=None,
        updated=False,
        skipped=True,
        error="pi extension not found or no package manager available",
    )


def refresh_global_skill() -> UpdateResult:
    """Re-install the bundled SKILL.md to ~/.claude/skills/sutras/.

    This is equivalent to running `sutras setup`.

    Returns:
        UpdateResult with outcome details.
    """
    target_dir = Path.home() / ".claude" / "skills" / "sutras"
    target_file = target_dir / "SKILL.md"

    try:
        from importlib.resources import files as resource_files

        skill_resource = resource_files("sutras").joinpath("data", "skills", "sutras", "SKILL.md")

        try:
            new_content = skill_resource.read_text(encoding="utf-8")
        except FileNotFoundError:
            return UpdateResult(
                component="global-skill",
                old_version=None,
                new_version=None,
                updated=False,
                skipped=True,
                error="Bundled SKILL.md not found in package data",
            )

        # Check if it actually changed
        old_content = None
        if target_file.exists():
            old_content = target_file.read_text(encoding="utf-8")

        if old_content == new_content:
            return UpdateResult(
                component="global-skill",
                old_version=__version__,
                new_version=__version__,
                updated=False,
                skipped=True,
            )

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(new_content)

        return UpdateResult(
            component="global-skill",
            old_version=None,
            new_version=__version__,
            updated=True,
        )

    except Exception as e:
        return UpdateResult(
            component="global-skill",
            old_version=None,
            new_version=None,
            updated=False,
            error=str(e),
        )


def update_all(
    target_version: str | None = None,
    skip_pi: bool = False,
    skip_skill: bool = False,
) -> UpdateSummary:
    """Run a full update: CLI + pi extension + global skill.

    Args:
        target_version: Pin to a specific version, or None for latest.
        skip_pi: Skip the pi extension update.
        skip_skill: Skip the global skill refresh.

    Returns:
        UpdateSummary with results for each component.
    """
    summary = UpdateSummary()

    # 1) Upgrade the Python CLI
    summary.results.append(upgrade_cli(target_version))

    # 2) Upgrade the pi extension
    if not skip_pi:
        summary.results.append(upgrade_pi_extension())
    else:
        summary.results.append(
            UpdateResult(
                component="pi-extension",
                old_version=None,
                new_version=None,
                updated=False,
                skipped=True,
            )
        )

    # 3) Refresh the global skill
    if not skip_skill:
        summary.results.append(refresh_global_skill())
    else:
        summary.results.append(
            UpdateResult(
                component="global-skill",
                old_version=None,
                new_version=None,
                updated=False,
                skipped=True,
            )
        )

    return summary

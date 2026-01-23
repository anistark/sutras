"""Semantic versioning and constraint parsing for Sutras.

Supports npm-style semver constraints:
- Exact: 1.0.0
- Caret: ^1.0.0 (compatible with 1.x.x)
- Tilde: ~1.2.3 (compatible with 1.2.x)
- Ranges: >=1.0.0 <2.0.0
- Wildcards: 1.x, 1.2.x, *
"""

import re
from dataclasses import dataclass


@dataclass
class Version:
    """Represents a semantic version."""

    major: int
    minor: int
    patch: int
    prerelease: str | None = None

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse a version string.

        Args:
            version_str: Version string (e.g., "1.2.3", "1.2.3-alpha")

        Returns:
            Parsed Version object

        Raises:
            ValueError: If version format is invalid
        """
        version_str = version_str.strip().lstrip("v")

        match = re.match(
            r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?$",
            version_str,
        )
        if not match:
            raise ValueError(f"Invalid version format: '{version_str}'")

        major, minor, patch, prerelease = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: "Version") -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        if self.prerelease is None and other.prerelease is None:
            return False
        if self.prerelease is None:
            return False
        if other.prerelease is None:
            return True
        return self.prerelease < other.prerelease

    def __le__(self, other: "Version") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        return self == other or self > other

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))


@dataclass
class VersionConstraint:
    """A single version constraint (e.g., >=1.0.0)."""

    operator: str
    version: Version

    def matches(self, version: Version) -> bool:
        """Check if a version matches this constraint."""
        if self.operator == "=":
            return version == self.version
        elif self.operator == ">":
            return version > self.version
        elif self.operator == ">=":
            return version >= self.version
        elif self.operator == "<":
            return version < self.version
        elif self.operator == "<=":
            return version <= self.version
        elif self.operator == "!=":
            return version != self.version
        return False


class VersionRange:
    """Represents a version range constraint (potentially multiple constraints)."""

    def __init__(self, constraints: list[VersionConstraint] | None = None):
        self.constraints = constraints or []

    @classmethod
    def parse(cls, constraint_str: str) -> "VersionRange":
        """Parse a version constraint string.

        Supports:
        - Exact: "1.0.0"
        - Caret: "^1.0.0" (>=1.0.0 <2.0.0)
        - Tilde: "~1.2.3" (>=1.2.3 <1.3.0)
        - Comparisons: ">=1.0.0", "<2.0.0", ">=1.0.0 <2.0.0"
        - Wildcards: "*", "1.x", "1.2.x"

        Args:
            constraint_str: Constraint string

        Returns:
            VersionRange object
        """
        constraint_str = constraint_str.strip()

        if not constraint_str or constraint_str == "*":
            return cls([VersionConstraint(">=", Version(0, 0, 0))])

        if constraint_str.endswith(".x") or constraint_str.endswith(".*"):
            return cls._parse_wildcard(constraint_str)

        if constraint_str.startswith("^"):
            return cls._parse_caret(constraint_str[1:])

        if constraint_str.startswith("~"):
            return cls._parse_tilde(constraint_str[1:])

        parts = re.split(r"\s+", constraint_str)
        constraints = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            match = re.match(r"^(>=|<=|>|<|!=|=)?(.+)$", part)
            if not match:
                raise ValueError(f"Invalid constraint: '{part}'")

            operator, version_str = match.groups()
            operator = operator or "="
            version = Version.parse(version_str)
            constraints.append(VersionConstraint(operator, version))

        if not constraints:
            raise ValueError(f"Invalid constraint string: '{constraint_str}'")

        return cls(constraints)

    @classmethod
    def _parse_caret(cls, version_str: str) -> "VersionRange":
        """Parse caret constraint (^1.0.0 -> >=1.0.0 <2.0.0)."""
        version = Version.parse(version_str)

        if version.major == 0:
            if version.minor == 0:
                upper = Version(0, 0, version.patch + 1)
            else:
                upper = Version(0, version.minor + 1, 0)
        else:
            upper = Version(version.major + 1, 0, 0)

        return cls(
            [
                VersionConstraint(">=", version),
                VersionConstraint("<", upper),
            ]
        )

    @classmethod
    def _parse_tilde(cls, version_str: str) -> "VersionRange":
        """Parse tilde constraint (~1.2.3 -> >=1.2.3 <1.3.0)."""
        version = Version.parse(version_str)
        upper = Version(version.major, version.minor + 1, 0)

        return cls(
            [
                VersionConstraint(">=", version),
                VersionConstraint("<", upper),
            ]
        )

    @classmethod
    def _parse_wildcard(cls, constraint_str: str) -> "VersionRange":
        """Parse wildcard constraint (1.x -> >=1.0.0 <2.0.0)."""
        parts = constraint_str.replace("*", "x").split(".")

        if len(parts) == 2 and parts[1] == "x":
            major = int(parts[0])
            return cls(
                [
                    VersionConstraint(">=", Version(major, 0, 0)),
                    VersionConstraint("<", Version(major + 1, 0, 0)),
                ]
            )
        elif len(parts) == 3 and parts[2] == "x":
            major = int(parts[0])
            minor = int(parts[1])
            return cls(
                [
                    VersionConstraint(">=", Version(major, minor, 0)),
                    VersionConstraint("<", Version(major, minor + 1, 0)),
                ]
            )

        raise ValueError(f"Invalid wildcard constraint: '{constraint_str}'")

    def matches(self, version: Version) -> bool:
        """Check if a version matches all constraints."""
        return all(c.matches(version) for c in self.constraints)

    def select_highest(self, versions: list[Version]) -> Version | None:
        """Select the highest version that matches the constraints.

        Args:
            versions: List of available versions

        Returns:
            Highest matching version, or None if no match
        """
        matching = [v for v in versions if self.matches(v)]
        if not matching:
            return None
        return max(matching)

    def __str__(self) -> str:
        if not self.constraints:
            return "*"
        parts = []
        for c in self.constraints:
            op = "" if c.operator == "=" else c.operator
            parts.append(f"{op}{c.version}")
        return " ".join(parts)


def parse_version(version_str: str) -> Version:
    """Parse a version string."""
    return Version.parse(version_str)


def parse_constraint(constraint_str: str) -> VersionRange:
    """Parse a version constraint string."""
    return VersionRange.parse(constraint_str)


def matches_constraint(version: str | Version, constraint: str | VersionRange) -> bool:
    """Check if a version matches a constraint.

    Args:
        version: Version string or object
        constraint: Constraint string or object

    Returns:
        True if version matches constraint
    """
    if isinstance(version, str):
        version = Version.parse(version)
    if isinstance(constraint, str):
        constraint = VersionRange.parse(constraint)
    return constraint.matches(version)


def select_version(
    versions: list[str] | list[Version],
    constraint: str | VersionRange,
) -> str | None:
    """Select the highest version matching a constraint.

    Args:
        versions: List of available versions
        constraint: Version constraint

    Returns:
        Highest matching version string, or None
    """
    if isinstance(constraint, str):
        constraint = VersionRange.parse(constraint)

    parsed_versions = []
    for v in versions:
        if isinstance(v, str):
            try:
                parsed_versions.append(Version.parse(v))
            except ValueError:
                continue
        else:
            parsed_versions.append(v)

    result = constraint.select_highest(parsed_versions)
    return str(result) if result else None

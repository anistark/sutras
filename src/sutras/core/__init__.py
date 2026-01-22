"""Core primitives for skill management and lifecycle."""

from sutras.core.abi import DependencyConfig, SutrasABI
from sutras.core.loader import SkillLoader
from sutras.core.lockfile import LockedSkill, Lockfile, LockfileManager
from sutras.core.resolver import (
    CircularDependencyError,
    DependencyConflictError,
    DependencyResolver,
    NoMatchingVersionError,
    ResolvedSkill,
    SkillNotFoundError,
    resolve_dependencies,
)
from sutras.core.semver import Version, VersionRange, parse_constraint, parse_version
from sutras.core.skill import Skill, SkillMetadata

__all__ = [
    "CircularDependencyError",
    "DependencyConfig",
    "DependencyConflictError",
    "DependencyResolver",
    "Lockfile",
    "LockedSkill",
    "LockfileManager",
    "NoMatchingVersionError",
    "ResolvedSkill",
    "Skill",
    "SkillLoader",
    "SkillMetadata",
    "SkillNotFoundError",
    "SutrasABI",
    "Version",
    "VersionRange",
    "parse_constraint",
    "parse_version",
    "resolve_dependencies",
]

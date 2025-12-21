"""
Ability - A Python devtool for creating, evaluating, testing, distributing,
and discovering Anthropic Agent Skills.

Ability provides a comprehensive CLI and library for managing the complete
skill lifecycle — from scaffolding to distribution.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ability")
except PackageNotFoundError:
    # Package is not installed, use fallback version
    __version__ = "0.0.0.dev0"

from ability.core.abi import AbilityABI
from ability.core.loader import SkillLoader
from ability.core.skill import Skill, SkillMetadata

__all__ = [
    "Skill",
    "SkillMetadata",
    "AbilityABI",
    "SkillLoader",
    "__version__",
]

"""
Sutras - A Python devtool for creating, evaluating, testing, distributing,
and discovering Anthropic Agent Skills.

Sutras provides a comprehensive CLI and library for managing the complete
skill lifecycle — from scaffolding to distribution.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sutras")
except PackageNotFoundError:
    # Package is not installed, use fallback version
    __version__ = "0.0.0.dev0"

from sutras.core.abi import SutrasABI
from sutras.core.loader import SkillLoader
from sutras.core.skill import Skill, SkillMetadata

__all__ = [
    "Skill",
    "SkillMetadata",
    "SutrasABI",
    "SkillLoader",
    "__version__",
]

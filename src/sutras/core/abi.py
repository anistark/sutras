"""Sutras ABI (Application Binary Interface) definitions.

Defines the schema for sutras.yaml files that extend Anthropic Skills
with lifecycle metadata for testing, evaluation, and distribution.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CapabilitiesConfig(BaseModel):
    """Capability declarations for a skill."""

    tools: list[str] = Field(default_factory=list, description="Required tools")
    dependencies: list[str] = Field(default_factory=list, description="Skill dependencies")
    constraints: dict[str, Any] = Field(default_factory=dict, description="Runtime constraints")


class TestCase(BaseModel):
    """A single test case specification."""

    name: str = Field(..., description="Test case name")
    description: str | None = Field(None, description="Test description")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Test inputs")
    expected: dict[str, Any] = Field(default_factory=dict, description="Expected outputs")
    timeout: int | None = Field(None, description="Test timeout in seconds")


class TestConfig(BaseModel):
    """Test configuration for a skill."""

    cases: list[TestCase] = Field(default_factory=list, description="Test cases")
    fixtures_dir: str | None = Field("tests/fixtures", description="Fixtures directory")
    coverage_threshold: float | None = Field(None, description="Minimum coverage percentage")


class EvalConfig(BaseModel):
    """Evaluation configuration for a skill."""

    framework: str = Field("ragas", description="Evaluation framework")
    metrics: list[str] = Field(default_factory=list, description="Metrics to compute")
    dataset: str | None = Field(None, description="Path to evaluation dataset")
    threshold: float | None = Field(None, description="Minimum score threshold")


class DistributionMetadata(BaseModel):
    """Distribution metadata for a skill."""

    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    category: str | None = Field(None, description="Skill category")
    homepage: str | None = Field(None, description="Homepage URL")
    documentation: str | None = Field(None, description="Documentation URL")
    keywords: list[str] = Field(default_factory=list, description="Search keywords")


class SutrasABI(BaseModel):
    """Complete Sutras ABI specification.

    This extends Anthropic Skills (SKILL.md) with lifecycle metadata
    stored in sutras.yaml.
    """

    # Core metadata
    version: str = Field(..., description="Semantic version (e.g., 1.0.0)")
    author: str | None = Field(None, description="Skill author")
    license: str = Field("MIT", description="License identifier")
    repository: str | None = Field(None, description="Source repository URL")

    # Capability declarations
    capabilities: CapabilitiesConfig | None = Field(None, description="Capability declarations")

    # Testing configuration
    tests: TestConfig | None = Field(None, description="Test configuration")

    # Evaluation configuration
    eval: EvalConfig | None = Field(None, description="Evaluation configuration")

    # Distribution metadata
    distribution: DistributionMetadata | None = Field(None, description="Distribution metadata")

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0.0",
                "author": "Skill Author",
                "license": "MIT",
                "repository": "https://github.com/user/skill",
                "capabilities": {
                    "tools": ["Read", "Write", "Bash"],
                    "dependencies": [],
                    "constraints": {},
                },
                "tests": {
                    "cases": [
                        {
                            "name": "basic-test",
                            "inputs": {"file": "test.txt"},
                            "expected": {"status": "success"},
                        }
                    ]
                },
                "eval": {
                    "framework": "ragas",
                    "metrics": ["correctness", "completeness"],
                    "dataset": "tests/eval/dataset.json",
                },
                "distribution": {
                    "tags": ["example", "demo"],
                    "category": "utilities",
                },
            }
        }
    )

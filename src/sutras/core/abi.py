"""Sutras ABI (Application Binary Interface) definitions.

Defines the schema for sutras.yaml files that extend Anthropic Skills
with lifecycle metadata for testing, evaluation, and distribution.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DependencyConfig(BaseModel):
    """Configuration for a single skill dependency."""

    name: str = Field(..., description="Dependency skill name (@namespace/name)")
    version: str = Field("*", description="Version constraint (e.g., ^1.0.0, ~1.2.3, >=1.0.0)")
    registry: str | None = Field(None, description="Specific registry to use")
    optional: bool = Field(False, description="Whether this dependency is optional")


class CapabilitiesConfig(BaseModel):
    """Capability declarations for a skill."""

    tools: list[str] = Field(default_factory=list, description="Required tools")
    dependencies: list[str | DependencyConfig] = Field(
        default_factory=list, description="Skill dependencies (strings or DependencyConfig)"
    )
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


AssertionType = Literal[
    "output_contains",
    "output_matches",
    "file_exists",
    "file_contains",
    "file_unchanged",
    "command_succeeds",
    "tool_called",
    "tool_not_called",
]

_ASSERTION_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "output_contains": ("text",),
    "output_matches": ("pattern",),
    "file_exists": ("path",),
    "file_contains": ("path", "text"),
    "file_unchanged": ("path",),
    "command_succeeds": ("run",),
    "tool_called": ("tool",),
    "tool_not_called": ("tool",),
}


class BenchAssertion(BaseModel):
    """A deterministic check run against a bench run's output or workspace."""

    type: AssertionType = Field(..., description="Assertion type")
    text: str | None = Field(None, description="Text to look for")
    pattern: str | None = Field(None, description="Regular expression to match")
    path: str | None = Field(None, description="Workspace-relative file path")
    run: str | None = Field(
        None, description="Shell command run in the workspace after the session"
    )
    tool: str | None = Field(None, description="Tool name (e.g. Edit, Bash)")
    timeout: int = Field(120, ge=1, description="Timeout in seconds for command_succeeds")

    @model_validator(mode="after")
    def _check_required_fields(self) -> "BenchAssertion":
        missing = [f for f in _ASSERTION_REQUIRED_FIELDS[self.type] if getattr(self, f) is None]
        if missing:
            raise ValueError(f"assertion '{self.type}' requires: {', '.join(missing)}")
        return self


class BenchCase(BaseModel):
    """A single benchmark scenario run against each model."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Case name")
    prompt: str = Field(..., description="Prompt sent to the agent")
    workspace: str | None = Field(
        None, description="Skill-relative directory copied into the sandbox as the project root"
    )
    should_trigger: bool = Field(True, description="Whether the skill is expected to load")
    assertions: list[BenchAssertion] = Field(
        default_factory=list, alias="assert", description="Deterministic checks"
    )
    rubric: list[str] = Field(default_factory=list, description="Criteria graded by the judge")
    allowed_tools: list[str] = Field(
        default_factory=list, description="Extra tools to pre-approve for this case"
    )


class BenchConfig(BaseModel):
    """Configuration for `sutras bench` cross-model benchmarking."""

    baseline: str | None = Field(None, description="Baseline model to compare against")
    models: list[str] = Field(
        default_factory=list, description="Models to bench (IDs or aliases, optional @effort)"
    )
    runs: int = Field(3, ge=1, description="Runs per case per model")
    max_regression: float = Field(
        0.10, ge=0, le=1, description="Max allowed pass-rate drop vs baseline"
    )
    max_cost: float | None = Field(None, gt=0, description="Hard spend cap in USD")
    timeout: int = Field(600, ge=1, description="Timeout per run in seconds")
    judge: str = Field("claude-opus-5-5", description="Fixed model used to grade rubrics")
    allowed_tools: list[str] = Field(
        default_factory=list, description="Tools to pre-approve for every case"
    )
    cases: list[BenchCase] = Field(default_factory=list, description="Bench cases")


class ModelCompatibility(BaseModel):
    """Recorded bench results for a single model."""

    pass_rate: float = Field(..., ge=0, le=1)
    trigger_rate: float = Field(..., ge=0, le=1)
    runs: int = Field(..., ge=0)
    regression: bool = False


class CompatibilityRecord(BaseModel):
    """Summary of a complete bench run, written by `sutras bench --record`."""

    runtime: str = Field(..., description="Agent runtime the bench ran on")
    runtime_version: str | None = Field(None, description="Runtime version")
    sutras_version: str = Field(..., description="Sutras version that ran the bench")
    benched_at: str = Field(..., description="Date of the bench run (YYYY-MM-DD)")
    skill_hash: str = Field(..., description="Hash of the skill files at bench time")
    baseline: str = Field(..., description="Baseline model")
    results: dict[str, ModelCompatibility] = Field(default_factory=dict)


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

    bench: BenchConfig | None = Field(None, description="Cross-model bench configuration")
    compatibility: CompatibilityRecord | None = Field(
        None, description="Recorded cross-model bench results"
    )

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
                    "dependencies": [
                        {"name": "@utils/helper", "version": "^1.0.0"},
                        "@tools/common",
                    ],
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

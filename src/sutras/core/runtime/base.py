"""Runtime executor interface for running skills against a model."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from sutras.core.pricing import ModelPrice


@dataclass
class TokenUsage:
    """Token counts reported for a run."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TokenUsage":
        data = data or {}
        return cls(
            input_tokens=int(data.get("input_tokens") or 0),
            output_tokens=int(data.get("output_tokens") or 0),
            cache_creation_input_tokens=int(data.get("cache_creation_input_tokens") or 0),
            cache_read_input_tokens=int(data.get("cache_read_input_tokens") or 0),
        )


@dataclass
class ToolCall:
    """A tool invocation observed during a run."""

    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunRequest:
    """Everything an executor needs for one headless agent run."""

    prompt: str
    model: str
    cwd: Path
    effort: str | None = None
    timeout: int = 600
    max_budget_usd: float | None = None
    allowed_tools: list[str] = field(default_factory=list)
    tools: list[str] | None = None
    """Restrict built-in tools. ``None`` keeps the defaults, ``[]`` disables all tools."""
    json_schema: dict[str, Any] | None = None


@dataclass
class RunResult:
    """Outcome of one headless agent run."""

    model: str
    final_text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    skills_invoked: list[str] = field(default_factory=list)
    num_turns: int = 0
    cost_usd: float | None = None
    """Reported cost; ``None`` when the run ended before reporting it (e.g. timeout)."""
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_s: float = 0.0
    error: str | None = None
    structured_output: Any = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class ModelInfo:
    """A model offered for benchmarking."""

    id: str
    display_name: str | None = None
    price: ModelPrice | None = None


@dataclass
class ModelDiscovery:
    """Models available to the runtime and where the list came from."""

    models: list[ModelInfo]
    source: Literal["api", "aliases"]
    note: str | None = None


class RuntimeExecutor(Protocol):
    """An agent runtime that can run a skill headlessly against a chosen model."""

    name: str

    def available(self) -> bool: ...

    def version(self) -> str | None: ...

    def discover_models(
        self, price_overrides: dict[str, ModelPrice] | None = None
    ) -> ModelDiscovery: ...

    def run(self, request: RunRequest) -> RunResult: ...

"""Model price table and model ID helpers used by `sutras bench`."""

import re
from dataclasses import dataclass

PRICES_AS_OF = "2026-09-25"
"""Date the built-in price table was last checked against Anthropic's published rates."""


@dataclass(frozen=True)
class ModelPrice:
    """Per-million-token prices in USD (Anthropic first-party API rates)."""

    input: float
    output: float

    @property
    def cache_read(self) -> float:
        return self.input * 0.1

    @property
    def cache_write(self) -> float:
        return self.input * 1.25

    def cost(
        self,
        input_tokens: float = 0,
        output_tokens: float = 0,
        cache_read_tokens: float = 0,
        cache_write_tokens: float = 0,
    ) -> float:
        """Cost in USD for the given token counts."""
        return (
            input_tokens * self.input
            + output_tokens * self.output
            + cache_read_tokens * self.cache_read
            + cache_write_tokens * self.cache_write
        ) / 1_000_000


DEFAULT_PRICES: dict[str, ModelPrice] = {
    "claude-fable-5-1": ModelPrice(10.0, 50.0),
    "claude-fable-5": ModelPrice(10.0, 50.0),
    "claude-opus-5-5": ModelPrice(4.0, 20.0),
    "claude-opus-5": ModelPrice(5.0, 25.0),
    "claude-opus-4-8": ModelPrice(5.0, 25.0),
    "claude-opus-4-7": ModelPrice(5.0, 25.0),
    "claude-opus-4-6": ModelPrice(5.0, 25.0),
    "claude-sonnet-5-5": ModelPrice(2.0, 10.0),
    "claude-sonnet-5": ModelPrice(2.0, 10.0),
    "claude-sonnet-4-6": ModelPrice(3.0, 15.0),
    "claude-haiku-4-5": ModelPrice(1.0, 5.0),
}

# NOTE: Claude Code resolves these aliases to the latest model of each family.
# The mapping is only used for pricing and display, so update it with new releases.
MODEL_ALIASES: dict[str, str] = {
    "fable": "claude-fable-5-1",
    "opus": "claude-opus-5-5",
    "sonnet": "claude-sonnet-5-5",
    "haiku": "claude-haiku-4-5",
}

DEFAULT_BENCH_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"]
"""Current-generation models benched by default when available."""

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")


def split_model_spec(spec: str) -> tuple[str, str | None]:
    """Split a ``model@effort`` spec into ``(model, effort)``.

    Raises:
        ValueError: If the effort level is not recognized
    """
    model, _, effort = spec.strip().partition("@")
    if effort and effort not in EFFORT_LEVELS:
        raise ValueError(
            f"Unknown effort '{effort}' in '{spec}' (expected one of: {', '.join(EFFORT_LEVELS)})"
        )
    return model, effort or None


def canonical_model_id(model: str) -> str:
    """Resolve aliases, drop ``@effort`` and date suffixes (``claude-haiku-4-5-20251001``)."""
    model, _ = split_model_spec(model)
    model = MODEL_ALIASES.get(model, model)
    return _DATE_SUFFIX_RE.sub("", model)


def get_price(model: str, overrides: dict[str, ModelPrice] | None = None) -> ModelPrice | None:
    """Look up the price for a model ID, alias, or ``model@effort`` spec."""
    canonical = canonical_model_id(model)
    if overrides:
        for key in (model, canonical):
            if key in overrides:
                return overrides[key]
    return DEFAULT_PRICES.get(canonical)

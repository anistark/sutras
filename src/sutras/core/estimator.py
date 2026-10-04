"""Pre-run cost estimation for `sutras bench`."""

from collections.abc import Callable
from dataclasses import dataclass, field

from sutras.core.bench import BenchPlan, BenchReport
from sutras.core.pricing import ModelPrice, canonical_model_id

CLAUDE_CODE_BASE_TOKENS = 20_000
"""Approximate system prompt + tool definitions sent on every Claude Code turn."""

JUDGE_BASE_TOKENS = 6_000

_HIGH_TURNS = 20

PriceLookup = Callable[[str], ModelPrice | None]
TokenCounter = Callable[[str, str], int | None]


@dataclass
class CostEstimate:
    """A cost range for a bench plan and how it was derived."""

    low: float
    high: float
    method: str
    detail: str
    per_run_high: float = 0.0
    per_model: dict[str, tuple[float, float]] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)


def approx_tokens(text: str) -> int:
    return len(text) // 4 + 1


def anthropic_token_counter() -> TokenCounter | None:
    """Token counter backed by ``messages.count_tokens``, or None if unavailable."""
    try:
        import anthropic  # type: ignore[import-not-found]

        client = anthropic.Anthropic(timeout=15.0, max_retries=1)
    except Exception:
        return None

    def count(text: str, model: str) -> int | None:
        try:
            response = client.messages.count_tokens(
                model=canonical_model_id(model),
                messages=[{"role": "user", "content": text}],
            )
            return int(response.input_tokens)
        except Exception:
            return None

    return count


def estimate_cost(
    plan: BenchPlan,
    price_of: PriceLookup,
    history: list[BenchReport] | None = None,
    count_tokens: TokenCounter | None = None,
) -> CostEstimate:
    """Estimate the cost range of a bench plan.

    Prefers per-run costs observed in this skill's bench history (including
    pilot runs). Falls back to a token heuristic: the fixed input (SKILL.md and
    case prompt) is counted exactly when a counter is available, while turns
    and output are assumed to range from a 3-turn run to a 20-turn run with
    growing context, both with Claude Code's prompt caching.
    """
    usable = [r for r in history or [] if r.records]
    if usable:
        return _from_history(plan, price_of, usable)
    return _from_heuristic(plan, price_of, count_tokens)


def _from_history(
    plan: BenchPlan, price_of: PriceLookup, history: list[BenchReport]
) -> CostEstimate:
    run_costs: dict[str, list[float]] = {}
    judge_costs: list[float] = []
    for report in history:
        for record in report.records:
            if record.cost_usd is not None:
                run_costs.setdefault(record.model, []).append(record.cost_usd)
            if record.rubric and record.judge_cost_usd:
                judge_costs.append(record.judge_cost_usd)

    def scaled(model: str) -> list[float] | None:
        if model in run_costs:
            return run_costs[model]
        price = price_of(model)
        for other, costs in run_costs.items():
            other_price = price_of(other)
            if price and other_price and other_price.output:
                ratio = price.output / other_price.output
                return [c * ratio for c in costs]
        return None

    judge_low, judge_high = _judge_range(plan, price_of)
    if judge_costs:
        mean = sum(judge_costs) / len(judge_costs)
        judge_low, judge_high = mean * 0.8, max(max(judge_costs), mean * 1.5)

    estimate = _empty(history)
    runs_per_model = len(plan.cases) * plan.runs
    judged_per_model = plan.runs * sum(1 for c in plan.cases if c.rubric)
    for model in plan.models:
        costs = scaled(model)
        if costs is None:
            estimate.unpriced.append(model)
            continue
        mean = sum(costs) / len(costs)
        low = mean * 0.8 * runs_per_model + judge_low * judged_per_model
        high = max(max(costs), mean * 1.5) * runs_per_model + judge_high * judged_per_model
        estimate.per_model[model] = (low, high)
        estimate.per_run_high = max(estimate.per_run_high, max(costs) + judge_high)
    return _total(estimate)


def _from_heuristic(
    plan: BenchPlan, price_of: PriceLookup, count_tokens: TokenCounter | None
) -> CostEstimate:
    skill_text = (plan.skill.path / "SKILL.md").read_text()
    exact = count_tokens is not None
    estimate = CostEstimate(
        low=0.0,
        high=0.0,
        method="heuristic",
        detail="token counts via count_tokens; turns and output assumed"
        if exact
        else "approximate token counts; turns and output assumed",
    )
    judge_low, judge_high = _judge_range(plan, price_of)

    for model in plan.models:
        price = price_of(model)
        if price is None:
            estimate.unpriced.append(model)
            continue
        low = high = 0.0
        for case in plan.cases:
            text = f"{skill_text}\n\n{case.prompt}"
            fixed = (count_tokens(text, model) if count_tokens else None) or approx_tokens(text)
            context = CLAUDE_CODE_BASE_TOKENS + fixed
            run_low = price.cost(
                cache_write_tokens=context, cache_read_tokens=2 * context, output_tokens=900
            )
            run_high = price.cost(
                cache_write_tokens=context + 3_000 * _HIGH_TURNS,
                cache_read_tokens=sum(context + 3_000 * turn for turn in range(_HIGH_TURNS)),
                output_tokens=1_500 * _HIGH_TURNS,
            )
            judged = judge_low if case.rubric else 0.0
            judged_high = judge_high if case.rubric else 0.0
            low += (run_low + judged) * plan.runs
            high += (run_high + judged_high) * plan.runs
            estimate.per_run_high = max(estimate.per_run_high, run_high + judged_high)
        estimate.per_model[model] = (low, high)
    return _total(estimate)


def _judge_range(plan: BenchPlan, price_of: PriceLookup) -> tuple[float, float]:
    price = price_of(plan.config.judge)
    if price is None:
        return 0.0, 0.0
    return (
        price.cost(input_tokens=JUDGE_BASE_TOKENS + 3_000, output_tokens=300),
        price.cost(input_tokens=JUDGE_BASE_TOKENS + 15_000, output_tokens=1_200),
    )


def _empty(history: list[BenchReport]) -> CostEstimate:
    latest = history[0]
    kind = "pilot" if latest.kind == "pilot" else "history"
    label = "pilot run" if kind == "pilot" else "last bench of this skill"
    return CostEstimate(low=0.0, high=0.0, method=kind, detail=f"{label}, {latest.started_at[:10]}")


def _total(estimate: CostEstimate) -> CostEstimate:
    estimate.low = sum(low for low, _ in estimate.per_model.values())
    estimate.high = sum(high for _, high in estimate.per_model.values())
    return estimate

"""Rubric grading for bench runs using a fixed judge model."""

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sutras.core.abi import BenchCase
from sutras.core.pricing import split_model_spec
from sutras.core.runtime.base import RunRequest, RunResult, RuntimeExecutor

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "pass": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["criterion", "pass", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}

_MAX_RESPONSE_CHARS = 8_000
_MAX_TOOL_CALLS = 60


@dataclass
class RubricVerdict:
    """The judge's verdict on one rubric criterion."""

    criterion: str
    passed: bool
    reason: str = ""


@dataclass
class JudgeResult:
    """All verdicts for one run, plus what grading cost."""

    verdicts: list[RubricVerdict] = field(default_factory=list)
    cost_usd: float | None = 0.0
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(v.passed for v in self.verdicts)


class Judge:
    """Grades a run against a case's rubric with a fixed model and no tools.

    The judge runs in an empty directory, so the skill under test never loads.
    """

    def __init__(self, executor: RuntimeExecutor, model: str, timeout: int = 300):
        self.executor = executor
        self.model = model
        self.timeout = timeout

    def grade(self, case: BenchCase, result: RunResult, diff: str) -> JudgeResult:
        if not case.rubric:
            return JudgeResult()

        model, effort = split_model_spec(self.model)
        with tempfile.TemporaryDirectory(prefix="sutras-judge-") as tmp:
            run = self.executor.run(
                RunRequest(
                    prompt=build_judge_prompt(case, result, diff),
                    model=model,
                    effort=effort,
                    cwd=Path(tmp),
                    timeout=self.timeout,
                    tools=[],
                    json_schema=JUDGE_SCHEMA,
                )
            )

        if run.error:
            return _failed(case, f"judge error: {run.error}", run.cost_usd)

        data = run.structured_output or _extract_json(run.final_text)
        raw = data.get("verdicts") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return _failed(case, "judge returned no verdicts", run.cost_usd)

        verdicts = []
        for i, criterion in enumerate(case.rubric):
            item = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
            verdicts.append(
                RubricVerdict(
                    criterion=criterion,
                    passed=item.get("pass") is True,
                    reason=str(item.get("reason", "no verdict returned")),
                )
            )
        return JudgeResult(verdicts=verdicts, cost_usd=run.cost_usd)


def build_judge_prompt(case: BenchCase, result: RunResult, diff: str) -> str:
    response = result.final_text
    if len(response) > _MAX_RESPONSE_CHARS:
        response = response[:_MAX_RESPONSE_CHARS] + "\n... (truncated)"

    calls = [
        f"- {call.name}: {json.dumps(call.input)[:200]}"
        for call in result.tool_calls[:_MAX_TOOL_CALLS]
    ]
    if len(result.tool_calls) > _MAX_TOOL_CALLS:
        calls.append(f"- ... and {len(result.tool_calls) - _MAX_TOOL_CALLS} more")

    rubric = "\n".join(f"{i}. {criterion}" for i, criterion in enumerate(case.rubric, start=1))

    return f"""You are grading one run of an AI coding agent against a rubric.
Judge only from the evidence below. Do not use tools.

## Task given to the agent
{case.prompt}

## Agent's final response
{response or "(empty)"}

## Tools the agent called
{chr(10).join(calls) or "(none)"}

## Workspace changes (unified diff)
{diff or "(no file changes)"}

## Rubric
{rubric}

Return one verdict per rubric criterion, in the same order. Set "pass" to true only
when the evidence clearly shows the criterion is met, and give a one-sentence reason.
"""


def _failed(case: BenchCase, reason: str, cost: float | None) -> JudgeResult:
    return JudgeResult(
        verdicts=[RubricVerdict(c, False, reason) for c in case.rubric], cost_usd=cost, error=reason
    )


def _extract_json(text: str) -> Any:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

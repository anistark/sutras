"""Cross-model skill benchmarking (`sutras bench`)."""

import hashlib
import json
import re
from collections.abc import Callable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from sutras.core.abi import BenchCase, BenchConfig, CompatibilityRecord, ModelCompatibility
from sutras.core.assertions import evaluate
from sutras.core.judge import Judge, JudgeResult, RubricVerdict
from sutras.core.pricing import split_model_spec
from sutras.core.runtime.base import RunRequest, RuntimeExecutor
from sutras.core.sandbox import Sandbox, skill_install_name
from sutras.core.skill import Skill

ReportKind = Literal["bench", "pilot"]


@dataclass
class BenchPlan:
    """The matrix of models × cases × runs to execute."""

    skill: Skill
    config: BenchConfig
    models: list[str]
    baseline: str
    cases: list[BenchCase]
    runs: int

    @property
    def total_runs(self) -> int:
        return len(self.models) * len(self.cases) * self.runs

    @property
    def judged_runs(self) -> int:
        return len(self.models) * self.runs * sum(1 for c in self.cases if c.rubric)

    @property
    def shell_commands(self) -> list[str]:
        commands: list[str] = []
        for case in self.cases:
            for assertion in case.assertions:
                if assertion.run and assertion.run not in commands:
                    commands.append(assertion.run)
        return commands

    @property
    def workspace_dirs(self) -> list[Path]:
        return [self.skill.path / c.workspace for c in self.config.cases if c.workspace]

    def jobs(self) -> Iterator[tuple[str, BenchCase, int]]:
        """Yield jobs round-robin across models so partial runs stay comparable."""
        for run in range(1, self.runs + 1):
            for case in self.cases:
                for model in self.models:
                    yield model, case, run

    def pilot(self) -> "BenchPlan":
        """One case, one run per model, used to calibrate the cost estimate."""
        return BenchPlan(
            skill=self.skill,
            config=self.config,
            models=self.models,
            baseline=self.baseline,
            cases=self.cases[:1],
            runs=1,
        )


@dataclass
class RunRecord:
    """Graded outcome of one model × case × run."""

    model: str
    case: str
    run: int
    passed: bool
    triggered: bool
    trigger_ok: bool
    assertions: list[dict[str, Any]] = field(default_factory=list)
    rubric: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float | None = None
    judge_cost_usd: float | None = None
    num_turns: int = 0
    duration_s: float = 0.0
    error: str | None = None

    @property
    def total_cost(self) -> float | None:
        if self.cost_usd is None:
            return None
        return self.cost_usd + (self.judge_cost_usd or 0.0)


@dataclass
class ModelSummary:
    """Aggregated results for one model."""

    model: str
    runs: int
    passed: int
    trigger_ok: int
    cost_usd: float
    delta: float | None = None
    regression: bool = False
    failed_cases: dict[str, tuple[int, int]] = field(default_factory=dict)
    untriggered_cases: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.runs if self.runs else 0.0

    @property
    def trigger_rate(self) -> float:
        return self.trigger_ok / self.runs if self.runs else 0.0


@dataclass
class BenchReport:
    """Everything recorded about one bench (or pilot) run."""

    skill: str
    skill_path: str
    skill_hash: str
    runtime: str
    runtime_version: str | None
    sutras_version: str
    started_at: str
    finished_at: str
    baseline: str
    models: list[str]
    cases: list[str]
    runs_per_case: int
    max_regression: float
    complete: bool
    stop_reason: str | None = None
    kind: ReportKind = "bench"
    records: list[RunRecord] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(r.total_cost or 0.0 for r in self.records)

    @property
    def unknown_cost_runs(self) -> int:
        return sum(1 for r in self.records if r.cost_usd is None)

    def summaries(self) -> list[ModelSummary]:
        summaries = []
        for model in self.models:
            records = [r for r in self.records if r.model == model]
            summary = ModelSummary(
                model=model,
                runs=len(records),
                passed=sum(r.passed for r in records),
                trigger_ok=sum(r.trigger_ok for r in records),
                cost_usd=sum(r.total_cost or 0.0 for r in records),
            )
            for case in self.cases:
                case_records = [r for r in records if r.case == case]
                passes = sum(r.passed for r in case_records)
                if case_records and passes < len(case_records):
                    summary.failed_cases[case] = (passes, len(case_records))
                if any(not r.trigger_ok for r in case_records):
                    summary.untriggered_cases.append(case)
            summaries.append(summary)

        baseline = next((s for s in summaries if s.model == self.baseline), None)
        if baseline and baseline.runs:
            for summary in summaries:
                if summary is baseline or not summary.runs:
                    continue
                summary.delta = summary.pass_rate - baseline.pass_rate
                summary.regression = summary.delta < -self.max_regression - 1e-9
        return summaries

    @property
    def has_regression(self) -> bool:
        return any(s.regression for s in self.summaries())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchReport":
        data = dict(data)
        data["records"] = [RunRecord(**r) for r in data.get("records", [])]
        return cls(**data)


class BenchRunner:
    """Executes a bench plan with parallelism and a hard spend cap.

    Before each run is scheduled, the largest per-run cost seen so far is
    reserved against ``max_cost``; when the next run could exceed the cap,
    scheduling stops and in-flight runs finish. Each run is also capped by
    Claude Code itself via ``--max-budget-usd`` with the remaining budget.
    """

    def __init__(
        self,
        plan: BenchPlan,
        executor: RuntimeExecutor,
        judge: Judge | None = None,
        max_cost: float | None = None,
        parallel: int = 2,
        keep_sandbox: bool = False,
        reserve_per_run: float = 0.0,
        on_record: Callable[[RunRecord], None] | None = None,
        sutras_version: str = "",
    ):
        self.plan = plan
        self.executor = executor
        self.judge = judge
        self.max_cost = max_cost
        self.parallel = max(1, parallel)
        self.keep_sandbox = keep_sandbox
        self.reserve_per_run = reserve_per_run
        self.on_record = on_record
        self.sutras_version = sutras_version
        self._install_name = skill_install_name(plan.skill)

    def run(self, kind: ReportKind = "bench") -> BenchReport:
        started = datetime.now()
        jobs = list(self.plan.jobs())
        records: list[RunRecord] = []
        stop_reason: str | None = None
        spent = 0.0
        largest = self.reserve_per_run
        seen_cost = False
        reserved: dict[Future[RunRecord], float] = {}
        job_iter = iter(jobs)
        next_job = next(job_iter, None)

        pool = ThreadPoolExecutor(max_workers=self.parallel)
        try:
            while True:
                while next_job is not None and len(reserved) < self.parallel:
                    budget = None
                    if self.max_cost is not None:
                        committed = spent + sum(reserved.values())
                        if (records or reserved) and committed + largest > self.max_cost:
                            if not reserved:
                                stop_reason = "cost cap reached"
                            break
                        budget = self.max_cost - committed
                    model_spec, case, run = next_job
                    future = pool.submit(self._run_job, model_spec, case, run, budget)
                    reserved[future] = largest
                    next_job = next(job_iter, None)

                if not reserved or stop_reason:
                    break

                done, _ = wait(list(reserved), return_when=FIRST_COMPLETED)
                for future in done:
                    reserved.pop(future)
                    record = future.result()
                    cost = record.total_cost
                    spent += cost if cost is not None else largest
                    if cost is not None:
                        largest = max(largest, cost) if seen_cost else cost
                        seen_cost = True
                    records.append(record)
                    if self.on_record:
                        self.on_record(record)
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            for future in reserved:
                future.cancel()
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        for future in reserved:
            if future.done() and not future.cancelled() and future.exception() is None:
                records.append(future.result())

        return BenchReport(
            skill=self.plan.skill.name,
            skill_path=str(self.plan.skill.path),
            skill_hash=compute_skill_hash(self.plan.skill),
            runtime=self.executor.name,
            runtime_version=self.executor.version(),
            sutras_version=self.sutras_version,
            started_at=started.isoformat(timespec="seconds"),
            finished_at=datetime.now().isoformat(timespec="seconds"),
            baseline=self.plan.baseline,
            models=list(self.plan.models),
            cases=[c.name for c in self.plan.cases],
            runs_per_case=self.plan.runs,
            max_regression=self.plan.config.max_regression,
            complete=stop_reason is None and len(records) == len(jobs),
            stop_reason=stop_reason,
            kind=kind,
            records=records,
        )

    def _run_job(
        self, model_spec: str, case: BenchCase, run: int, budget: float | None
    ) -> RunRecord:
        try:
            return self._grade_job(model_spec, case, run, budget)
        except Exception as e:
            return RunRecord(
                model=model_spec,
                case=case.name,
                run=run,
                passed=False,
                triggered=False,
                trigger_ok=False,
                cost_usd=0.0,
                error=f"{type(e).__name__}: {e}",
            )

    def _grade_job(
        self, model_spec: str, case: BenchCase, run: int, budget: float | None
    ) -> RunRecord:
        model, effort = split_model_spec(model_spec)
        config = self.plan.config
        workspace = self.plan.skill.path / case.workspace if case.workspace else None

        with Sandbox(
            self.plan.skill, workspace, keep=self.keep_sandbox, exclude=self.plan.workspace_dirs
        ) as sandbox:
            result = self.executor.run(
                RunRequest(
                    prompt=case.prompt,
                    model=model,
                    effort=effort,
                    cwd=sandbox.root,
                    timeout=config.timeout,
                    max_budget_usd=budget,
                    allowed_tools=[*config.allowed_tools, *case.allowed_tools],
                )
            )
            triggered = any(
                s == self._install_name or s.endswith(f":{self._install_name}")
                for s in result.skills_invoked
            )
            outcomes = [evaluate(a, result, sandbox) for a in case.assertions]
            trigger_ok = triggered == case.should_trigger
            already_failed = not trigger_ok or not all(o.passed for o in outcomes)

            if not case.rubric:
                judged = JudgeResult()
            elif self.judge and result.ok and not already_failed:
                judged = self.judge.grade(case, result, sandbox.diff())
            else:
                if not result.ok:
                    reason = "skipped: run failed"
                elif already_failed:
                    reason = "skipped: run already failed"
                else:
                    reason = "skipped: no judge"
                judged = JudgeResult(
                    verdicts=[RubricVerdict(c, False, reason) for c in case.rubric],
                    error=reason,
                )

        return RunRecord(
            model=model_spec,
            case=case.name,
            run=run,
            passed=result.ok and trigger_ok and all(o.passed for o in outcomes) and judged.passed,
            triggered=triggered,
            trigger_ok=trigger_ok,
            assertions=[asdict(o) for o in outcomes],
            rubric=[asdict(v) for v in judged.verdicts],
            cost_usd=result.cost_usd,
            judge_cost_usd=judged.cost_usd,
            num_turns=result.num_turns,
            duration_s=round(result.duration_s, 2),
            error=result.error,
        )


def compute_skill_hash(skill: Skill) -> str:
    """Hash SKILL.md and supporting files (not sutras.yaml, which `--record` rewrites)."""
    digest = hashlib.sha256()
    files = {"SKILL.md": skill.path / "SKILL.md", **skill.supporting_files}
    for name in sorted(files):
        digest.update(name.encode() + b"\0")
        digest.update(files[name].read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def history_dir(skill: Skill) -> Path:
    return skill.path / ".sutras" / "bench"


def save_report(report: BenchReport, skill: Skill) -> Path:
    """Write a report to the skill's bench history and return its path."""
    directory = history_dir(skill)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.replace(":", "-")
    suffix = "-pilot" if report.kind == "pilot" else ""
    path = directory / f"{stamp}{suffix}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2))
    return path


def load_history(skill: Skill) -> list[tuple[Path, BenchReport]]:
    """Load saved reports, newest first. Unreadable files are skipped."""
    directory = history_dir(skill)
    if not directory.is_dir():
        return []
    reports = []
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            reports.append((path, BenchReport.from_dict(json.loads(path.read_text()))))
        except (OSError, ValueError, TypeError):
            continue
    return reports


def latest_complete_report(skill: Skill) -> BenchReport | None:
    for _, report in load_history(skill):
        if report.kind == "bench" and report.complete:
            return report
    return None


def build_compatibility(report: BenchReport) -> CompatibilityRecord:
    return CompatibilityRecord(
        runtime=report.runtime,
        runtime_version=report.runtime_version,
        sutras_version=report.sutras_version,
        benched_at=report.started_at[:10],
        skill_hash=report.skill_hash,
        baseline=report.baseline,
        results={
            s.model: ModelCompatibility(
                pass_rate=round(s.pass_rate, 3),
                trigger_rate=round(s.trigger_rate, 3),
                runs=s.runs,
                regression=s.regression,
            )
            for s in report.summaries()
        },
    )


def write_compatibility(sutras_yaml: Path, record: CompatibilityRecord) -> None:
    """Replace the top-level ``compatibility`` block, leaving the rest of the file as written."""
    kept: list[str] = []
    skipping = False
    for line in sutras_yaml.read_text().splitlines(keepends=True):
        if re.match(r"^compatibility\s*:", line):
            skipping = True
            continue
        if skipping:
            if not line.strip() or line[0] in " \t":
                continue
            skipping = False
        kept.append(line)

    block = yaml.safe_dump({"compatibility": record.model_dump(exclude_none=True)}, sort_keys=False)
    text = "".join(kept).rstrip("\n")
    sutras_yaml.write_text(f"{text}\n\n{block}" if text else block)


def render_markdown(report: BenchReport) -> str:
    """Render a Markdown summary suitable for PR comments."""
    lines = [
        f"## Bench: `{report.skill}`",
        "",
        f"Runtime: {report.runtime} {report.runtime_version or ''}".rstrip()
        + f" · {report.runs_per_case} run(s) per case · baseline `{report.baseline}`",
        "",
        "| Model | Trigger | Pass rate | vs baseline | Cost |",
        "|---|---|---|---|---|",
    ]
    for s in report.summaries():
        if s.delta is None:
            verdict = "—"
        else:
            verdict = f"{s.delta * 100:+.0f}% {'❌' if s.regression else '✅'}"
        lines.append(
            f"| `{s.model}` | {s.trigger_ok}/{s.runs} | {s.pass_rate:.0%} | {verdict} "
            f"| ${s.cost_usd:.2f} |"
        )

    failures = [s for s in report.summaries() if s.failed_cases or s.untriggered_cases]
    if failures:
        lines += ["", "### Failures", ""]
        for s in failures:
            for case, (passes, runs) in s.failed_cases.items():
                lines.append(f"- `{s.model}` · `{case}`: {passes}/{runs} passed")
            if s.untriggered_cases:
                cases = ", ".join(f"`{c}`" for c in s.untriggered_cases)
                lines.append(f"- `{s.model}` · wrong trigger behavior on: {cases}")

    status = "complete" if report.complete else f"incomplete ({report.stop_reason})"
    lines += ["", f"Total cost: ${report.total_cost:.2f} · {status} · {report.started_at}", ""]
    return "\n".join(lines)

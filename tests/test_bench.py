"""Tests for `sutras bench` and its core modules (no real model calls)."""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from pydantic import ValidationError

from sutras import Skill
from sutras.cli import main as cli_main
from sutras.cli.main import cli
from sutras.core.abi import BenchAssertion, BenchCase, SutrasABI
from sutras.core.assertions import evaluate
from sutras.core.bench import (
    BenchPlan,
    BenchReport,
    BenchRunner,
    RunRecord,
    build_compatibility,
    compute_skill_hash,
    latest_complete_report,
    load_history,
    render_markdown,
    save_report,
    write_compatibility,
)
from sutras.core.estimator import estimate_cost
from sutras.core.judge import Judge
from sutras.core.pricing import ModelPrice, canonical_model_id, get_price, split_model_spec
from sutras.core.registry import RegistryManager
from sutras.core.runtime import (
    ClaudeCodeExecutor,
    ModelDiscovery,
    ModelInfo,
    RunRequest,
    RunResult,
    ToolCall,
    parse_stream_json,
)
from sutras.core.sandbox import Sandbox

SKILL_MD = """---
name: greeter
description: Writes friendly greeting files when the user asks to greet someone by name
---

When asked to greet someone, create greeting.txt containing "Hello, <name>!".
"""

SUTRAS_YAML = """version: "0.1.0"
author: "Test"
license: "MIT"
bench:
  baseline: claude-opus-5-5
  models: [claude-opus-5-5, claude-haiku-4-5]
  runs: 2
  cases:
    - name: greet-alice
      prompt: "Please greet Alice"
      workspace: bench/hello
      assert:
        - type: file_contains
          path: greeting.txt
          text: "Hello, Alice!"
        - type: file_unchanged
          path: README.md
      rubric:
        - Does not modify README.md
    - name: unrelated
      prompt: "What is 2 + 2?"
      should_trigger: false
"""


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    path = tmp_path / "greeter"
    (path / "bench" / "hello").mkdir(parents=True)
    (path / "bench" / "hello" / "README.md").write_text("# hello\n")
    (path / "SKILL.md").write_text(SKILL_MD)
    (path / "sutras.yaml").write_text(SUTRAS_YAML)
    return path


class FakeExecutor:
    """Executor that simulates Claude Code without calling a model.

    Models listed in ``no_trigger`` never load the skill. Judge calls (requests
    with a JSON schema) pass every criterion.
    """

    name = "fake"

    def __init__(self, no_trigger: set[str] | None = None, cost: float = 0.10):
        self.no_trigger = no_trigger or set()
        self.cost = cost
        self.requests: list[RunRequest] = []

    def available(self) -> bool:
        return True

    def version(self) -> str | None:
        return "9.9.9"

    def discover_models(self, price_overrides=None) -> ModelDiscovery:
        return ModelDiscovery(
            models=[
                ModelInfo(m, price=get_price(m))
                for m in ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"]
            ],
            source="api",
        )

    def run(self, request: RunRequest) -> RunResult:
        self.requests.append(request)
        if request.json_schema:
            return RunResult(
                model=request.model,
                structured_output={
                    "verdicts": [{"criterion": "c", "pass": True, "reason": "README untouched"}]
                },
                cost_usd=0.01,
            )
        triggers = request.model not in self.no_trigger and "greet" in request.prompt.lower()
        if triggers:
            (request.cwd / "greeting.txt").write_text("Hello, Alice!")
        return RunResult(
            model=request.model,
            final_text="Done",
            tool_calls=[ToolCall("Write", {"file_path": "greeting.txt"})] if triggers else [],
            skills_invoked=["greeter"] if triggers else [],
            num_turns=3,
            cost_usd=self.cost,
        )


def _plan(skill: Skill, **overrides) -> BenchPlan:
    assert skill.abi and skill.abi.bench
    config = skill.abi.bench
    params = {
        "skill": skill,
        "config": config,
        "models": list(config.models),
        "baseline": config.baseline or config.models[0],
        "cases": list(config.cases),
        "runs": config.runs,
    }
    params.update(overrides)
    return BenchPlan(**params)


def _runner(plan: BenchPlan, executor: FakeExecutor, **kwargs) -> BenchRunner:
    return BenchRunner(plan, executor, judge=Judge(executor, "claude-opus-5-5"), **kwargs)


class TestPricing:
    def test_canonical_model_id(self):
        assert canonical_model_id("opus") == "claude-opus-5-5"
        assert canonical_model_id("claude-haiku-4-5-20251001") == "claude-haiku-4-5"
        assert canonical_model_id("sonnet@low") == "claude-sonnet-5-5"

    def test_split_model_spec(self):
        assert split_model_spec("claude-opus-5-5@high") == ("claude-opus-5-5", "high")
        assert split_model_spec("opus") == ("opus", None)
        with pytest.raises(ValueError, match="Unknown effort"):
            split_model_spec("opus@turbo")

    def test_get_price_with_overrides(self):
        assert get_price("haiku") == ModelPrice(1.0, 5.0)
        assert get_price("custom-model") is None
        override = {"claude-opus-5-5": ModelPrice(1.0, 2.0)}
        assert get_price("opus", override) == ModelPrice(1.0, 2.0)

    def test_cost(self):
        price = ModelPrice(4.0, 20.0)
        assert price.cost(input_tokens=1_000_000, output_tokens=1_000_000) == 24.0
        assert price.cost(cache_read_tokens=1_000_000) == pytest.approx(0.4)


class TestAbi:
    def test_assert_alias_and_required_fields(self):
        abi = SutrasABI.model_validate(yaml.safe_load(SUTRAS_YAML))
        assert abi.bench and abi.bench.cases[0].assertions[0].type == "file_contains"
        with pytest.raises(ValidationError, match="requires: text"):
            BenchAssertion(type="output_contains")


class TestStreamParsing:
    def test_parses_result_tools_and_skills(self):
        events = [
            {"type": "system", "subtype": "init", "model": "claude-opus-5-5"},
            {
                "type": "assistant",
                "parent_tool_use_id": None,
                "message": {
                    "content": [
                        {"type": "text", "text": "Loading skill"},
                        {"type": "tool_use", "name": "Skill", "input": {"skill": "greeter"}},
                        {"type": "tool_use", "name": "Write", "input": {"file_path": "g.txt"}},
                    ]
                },
            },
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "All done",
                "num_turns": 4,
                "total_cost_usd": 0.0123,
                "usage": {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 5},
            },
        ]
        stdout = "\n".join(json.dumps(e) for e in events) + "\nnot json\n"
        result = parse_stream_json(stdout, "claude-opus-5-5")
        assert result.ok
        assert result.final_text == "All done"
        assert result.skills_invoked == ["greeter"]
        assert [c.name for c in result.tool_calls] == ["Skill", "Write"]
        assert result.num_turns == 4
        assert result.cost_usd == pytest.approx(0.0123)
        assert result.usage.cache_read_input_tokens == 5

    def test_error_result(self):
        stdout = json.dumps({"type": "result", "subtype": "error_max_budget_usd", "is_error": True})
        result = parse_stream_json(stdout, "m")
        assert result.error and "error_max_budget_usd" in result.error

    def test_missing_result_event(self):
        assert parse_stream_json("", "m").error == "Claude Code produced no result event"

    def test_build_command_isolation_and_options(self, tmp_path):
        cmd = ClaudeCodeExecutor().build_command(
            RunRequest(
                prompt="hi",
                model="claude-haiku-4-5",
                cwd=tmp_path,
                effort="low",
                max_budget_usd=1.5,
                allowed_tools=["Bash(pytest *)"],
                tools=[],
            )
        )
        joined = " ".join(cmd)
        for flag in [
            "-p",
            "--output-format stream-json",
            "--verbose",
            "--setting-sources project",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--permission-prompts none",
            "--effort low",
            "--max-budget-usd 1.5000",
        ]:
            assert flag in joined
        assert cmd[cmd.index("--tools") + 1] == ""
        assert cmd[-1] == "Bash(pytest *)"


class TestSandbox:
    def test_installs_skill_and_copies_workspace(self, skill_dir):
        skill = Skill.load(skill_dir)
        (skill_dir / ".sutras").mkdir()
        workspace = skill_dir / "bench" / "hello"
        with Sandbox(skill, workspace, exclude=[workspace]) as sandbox:
            installed = sandbox.root / ".claude" / "skills" / "greeter"
            assert (installed / "SKILL.md").exists()
            assert not (installed / ".sutras").exists()
            assert not (installed / "bench" / "hello").exists()
            assert (sandbox.root / "README.md").exists()
            (sandbox.root / "README.md").write_text("# changed\n")
            assert "-# hello" in sandbox.diff()
            with pytest.raises(ValueError, match="outside the workspace"):
                sandbox.resolve("../escape.txt")
            root = sandbox.root
        assert not root.exists()

    def test_scoped_name_installs_bare_dir(self, tmp_path):
        path = tmp_path / "tool"
        path.mkdir()
        (path / "SKILL.md").write_text("---\nname: '@acme/tool'\ndescription: d\n---\n\nBody\n")
        with Sandbox(Skill.load(path)) as sandbox:
            assert (sandbox.root / ".claude" / "skills" / "tool" / "SKILL.md").exists()


class TestAssertions:
    def test_all_types(self, skill_dir):
        skill = Skill.load(skill_dir)
        workspace = skill_dir / "bench" / "hello"
        result = RunResult(
            model="m", final_text="Created greeting 42", tool_calls=[ToolCall("Edit")]
        )
        with Sandbox(skill, workspace) as sandbox:
            (sandbox.root / "greeting.txt").write_text("Hello, Alice!")
            cases = [
                (BenchAssertion(type="output_contains", text="greeting"), True),
                (BenchAssertion(type="output_matches", pattern=r"\d+"), True),
                (BenchAssertion(type="file_exists", path="greeting.txt"), True),
                (BenchAssertion(type="file_contains", path="greeting.txt", text="Alice"), True),
                (BenchAssertion(type="file_contains", path="missing.txt", text="x"), False),
                (BenchAssertion(type="file_unchanged", path="README.md"), True),
                (BenchAssertion(type="file_unchanged", path="greeting.txt"), False),
                (BenchAssertion(type="command_succeeds", run="test -f greeting.txt"), True),
                (BenchAssertion(type="command_succeeds", run="exit 3"), False),
                (BenchAssertion(type="tool_called", tool="Edit"), True),
                (BenchAssertion(type="tool_not_called", tool="Edit"), False),
                (BenchAssertion(type="file_exists", path="../../etc/passwd"), False),
            ]
            for assertion, expected in cases:
                assert evaluate(assertion, result, sandbox).passed is expected, assertion


class TestRunner:
    def test_summaries_and_regression(self, skill_dir):
        skill = Skill.load(skill_dir)
        executor = FakeExecutor(no_trigger={"claude-haiku-4-5"})
        report = _runner(_plan(skill), executor, sutras_version="1.0").run()

        assert report.complete
        assert len(report.records) == 8
        opus, haiku = report.summaries()
        assert opus.pass_rate == 1.0 and opus.trigger_rate == 1.0
        assert haiku.pass_rate == 0.5
        assert haiku.untriggered_cases == ["greet-alice"]
        assert haiku.failed_cases == {"greet-alice": (0, 2)}
        assert haiku.regression and report.has_regression
        assert report.total_cost == pytest.approx(8 * 0.10 + 2 * 0.01)

    def test_judge_skipped_when_run_fails(self, skill_dir):
        skill = Skill.load(skill_dir)

        class FailingExecutor(FakeExecutor):
            def run(self, request):
                return RunResult(model=request.model, error="boom", cost_usd=0.0)

        report = _runner(_plan(skill, runs=1), FailingExecutor()).run()
        greet = next(r for r in report.records if r.case == "greet-alice")
        assert not greet.passed and greet.rubric[0]["reason"] == "skipped: run failed"

    def test_cost_cap_stops_scheduling(self, skill_dir):
        skill = Skill.load(skill_dir)
        executor = FakeExecutor(cost=1.0)
        report = _runner(_plan(skill), executor, max_cost=2.5, parallel=1).run()
        assert not report.complete
        assert report.stop_reason == "cost cap reached"
        assert len(report.records) < 8
        budgets = [r.max_budget_usd for r in executor.requests if not r.json_schema]
        assert budgets[0] == pytest.approx(2.5)
        assert budgets == sorted(budgets, reverse=True)

    def test_effort_spec_passed_to_executor(self, skill_dir):
        skill = Skill.load(skill_dir)
        executor = FakeExecutor()
        plan = _plan(skill, models=["claude-sonnet-5-5@low"], baseline="claude-sonnet-5-5@low")
        _runner(plan, executor).run()
        run_requests = [r for r in executor.requests if not r.json_schema]
        assert {(r.model, r.effort) for r in run_requests} == {("claude-sonnet-5-5", "low")}


class TestReportsAndRecording:
    def _report(self, skill_dir: Path) -> tuple[Skill, BenchReport]:
        skill = Skill.load(skill_dir)
        return skill, _runner(_plan(skill), FakeExecutor({"claude-haiku-4-5"})).run()

    def test_history_roundtrip(self, skill_dir):
        skill, report = self._report(skill_dir)
        path = save_report(report, skill)
        assert path.parent == skill_dir / ".sutras" / "bench"
        loaded = load_history(skill)[0][1]
        assert loaded.records == report.records
        assert latest_complete_report(skill) is not None

    def test_markdown(self, skill_dir):
        _, report = self._report(skill_dir)
        md = render_markdown(report)
        assert "| `claude-haiku-4-5` | 2/4 | 50% | -50% ❌" in md
        assert "wrong trigger behavior on: `greet-alice`" in md

    def test_write_compatibility_preserves_file(self, skill_dir):
        _, report = self._report(skill_dir)
        sutras_yaml = skill_dir / "sutras.yaml"
        sutras_yaml.write_text("# keep me\n" + SUTRAS_YAML + "compatibility:\n  old: true\n")
        write_compatibility(sutras_yaml, build_compatibility(report))
        write_compatibility(sutras_yaml, build_compatibility(report))
        text = sutras_yaml.read_text()
        assert text.startswith("# keep me\n")
        assert text.count("compatibility:") == 1
        assert "old: true" not in text
        abi = SutrasABI.model_validate(yaml.safe_load(text))
        assert abi.compatibility and abi.compatibility.results["claude-haiku-4-5"].regression

    def test_skill_hash_ignores_sutras_yaml(self, skill_dir):
        before = compute_skill_hash(Skill.load(skill_dir))
        (skill_dir / "sutras.yaml").write_text(SUTRAS_YAML + "# edit\n")
        assert compute_skill_hash(Skill.load(skill_dir)) == before
        (skill_dir / "SKILL.md").write_text(SKILL_MD + "More.\n")
        assert compute_skill_hash(Skill.load(skill_dir)) != before


class TestEstimator:
    def test_heuristic_range_and_unpriced(self, skill_dir):
        skill = Skill.load(skill_dir)
        plan = _plan(skill, models=["claude-opus-5-5", "mystery-model"])
        estimate = estimate_cost(plan, get_price, history=[], count_tokens=lambda t, m: 500)
        assert estimate.method == "heuristic"
        assert "count_tokens" in estimate.detail
        assert 0 < estimate.low < estimate.high
        assert estimate.unpriced == ["mystery-model"]

    def test_history_scales_missing_models_by_price(self, skill_dir):
        skill = Skill.load(skill_dir)
        record = RunRecord(
            model="claude-haiku-4-5",
            case="greet-alice",
            run=1,
            passed=True,
            triggered=True,
            trigger_ok=True,
            cost_usd=0.10,
        )
        history = BenchReport(
            skill="greeter",
            skill_path="",
            skill_hash="",
            runtime="fake",
            runtime_version=None,
            sutras_version="",
            started_at="2026-10-01T00:00:00",
            finished_at="2026-10-01T00:01:00",
            baseline="claude-haiku-4-5",
            models=["claude-haiku-4-5"],
            cases=["greet-alice"],
            runs_per_case=1,
            max_regression=0.1,
            complete=True,
            records=[record],
        )
        plan = _plan(skill, models=["claude-opus-5-5", "claude-haiku-4-5"])
        estimate = estimate_cost(plan, get_price, history=[history])
        assert estimate.method == "history"
        opus_low, _ = estimate.per_model["claude-opus-5-5"]
        haiku_low, _ = estimate.per_model["claude-haiku-4-5"]
        assert opus_low > haiku_low


class TestCli:
    @pytest.fixture(autouse=True)
    def fake_runtime(self, monkeypatch):
        executor = FakeExecutor(no_trigger={"claude-haiku-4-5"})
        monkeypatch.setattr(cli_main, "ClaudeCodeExecutor", lambda: executor)
        monkeypatch.setattr(cli_main, "anthropic_token_counter", lambda: None)

        class _Config:
            def get_price_overrides(self):
                return {}

        monkeypatch.setattr(cli_main, "SutrasConfig", _Config)
        return executor

    def _invoke(self, *args: str, input: str | None = None):
        return CliRunner().invoke(cli, ["bench", *args], input=input)

    def test_dry_run_shows_plan_without_running(self, skill_dir, fake_runtime):
        result = self._invoke(str(skill_dir), "--dry-run")
        assert result.exit_code == 0, result.output
        assert "[x] claude-opus-5-5" in result.output
        assert "(baseline)" in result.output
        assert "[ ] claude-sonnet-5-5" in result.output
        assert "2 case(s) × 2 run(s) × 2 model(s) = 8 runs + 4 judge calls" in result.output
        assert "Estimate:" in result.output
        assert fake_runtime.requests == []

    def test_yes_requires_max_cost(self, skill_dir):
        result = self._invoke(str(skill_dir), "--yes")
        assert result.exit_code != 0
        assert "--yes requires --max-cost" in result.output

    def test_declining_approval_spends_nothing(self, skill_dir, fake_runtime, monkeypatch):
        monkeypatch.setattr(cli_main.sys.stdin, "isatty", lambda: True, raising=False)
        result = self._invoke(str(skill_dir), input="n\n")
        assert result.exit_code != 0
        assert fake_runtime.requests == []

    def test_full_run_saves_history_and_exits_on_regression(self, skill_dir):
        result = self._invoke(str(skill_dir), "--yes", "--max-cost", "10", "--report", "md")
        assert result.exit_code == 1, result.output
        assert "claude-haiku-4-5: wrong trigger behavior on: greet-alice" in result.output
        assert list((skill_dir / ".sutras" / "bench").glob("*.md"))
        assert "sutras bench" in result.output and "--record" in result.output

    def test_models_option_and_case_subset(self, skill_dir, fake_runtime):
        result = self._invoke(
            str(skill_dir),
            "--models",
            "opus,sonnet",
            "--cases",
            "unrelated",
            "--runs",
            "1",
            "--yes",
            "--max-cost",
            "5",
        )
        assert result.exit_code == 0, result.output
        models = {r.model for r in fake_runtime.requests}
        assert models == {"claude-opus-5-5", "opus", "sonnet"}

    def test_unknown_case(self, skill_dir):
        result = self._invoke(str(skill_dir), "--cases", "nope", "--dry-run")
        assert result.exit_code != 0
        assert "Unknown case(s): nope" in result.output

    def test_no_bench_section(self, tmp_path):
        path = tmp_path / "plain"
        path.mkdir()
        (path / "SKILL.md").write_text(SKILL_MD.replace("greeter", "plain"))
        result = self._invoke(str(path), "--dry-run")
        assert result.exit_code != 0
        assert "has no bench cases" in result.output

    def test_record_history_validate_and_info(self, skill_dir, monkeypatch):
        assert self._invoke(str(skill_dir), "--record").exit_code != 0

        self._invoke(str(skill_dir), "--yes", "--max-cost", "10")
        history = self._invoke(str(skill_dir), "--history")
        assert "complete" in history.output and "claude-opus-5-5 100%" in history.output

        recorded = self._invoke(str(skill_dir), "--record")
        assert recorded.exit_code == 0, recorded.output
        abi = SutrasABI.model_validate(yaml.safe_load((skill_dir / "sutras.yaml").read_text()))
        assert abi.compatibility and abi.compatibility.baseline == "claude-opus-5-5"

        validate = CliRunner().invoke(cli, ["validate", str(skill_dir)])
        assert "Tested on: claude-opus-5-5 100%" in validate.output

        (skill_dir / "SKILL.md").write_text(SKILL_MD + "\nExtra line.\n")
        validate = CliRunner().invoke(cli, ["validate", str(skill_dir)])
        assert "Recorded bench results are stale" in validate.output
        assert (
            "Re-run `sutras bench` before recording"
            in self._invoke(str(skill_dir), "--record").output
        )

        skills_root = skill_dir.parent / ".claude" / "skills"
        skills_root.mkdir(parents=True)
        (skills_root / "greeter").symlink_to(skill_dir)
        monkeypatch.chdir(skill_dir.parent)
        info = CliRunner().invoke(cli, ["info", "greeter"])
        assert "Tested on (fake" in info.output
        assert "Stale" in info.output


class TestValidateBench:
    def test_bad_bench_config(self, skill_dir):
        text = SUTRAS_YAML.replace("workspace: bench/hello", "workspace: bench/missing")
        text = text.replace("name: unrelated", "name: greet-alice")
        text = text.replace("models: [claude-opus-5-5, claude-haiku-4-5]", "models: [opus@turbo]")
        (skill_dir / "sutras.yaml").write_text(text)
        result = CliRunner().invoke(cli, ["validate", str(skill_dir)])
        assert result.exit_code != 0
        assert "Duplicate case name(s): greet-alice" in result.output
        assert "Unknown effort 'turbo'" in result.output
        assert "workspace 'bench/missing' not found" in result.output


def test_build_index_includes_compatibility(tmp_path):
    skill = tmp_path / "skills" / "greeter"
    skill.mkdir(parents=True)
    (skill / "sutras.yaml").write_text(
        'version: "1.0.0"\ncompatibility:\n  baseline: opus\n  results: {}\n'
    )
    RegistryManager.build_index(None, tmp_path)  # type: ignore[arg-type]
    index = yaml.safe_load((tmp_path / "index.yaml").read_text())
    assert index["skills"]["greeter"]["compatibility"]["baseline"] == "opus"


def test_case_model_roundtrip():
    case = BenchCase.model_validate({"name": "c", "prompt": "p", "assert": []})
    assert case.should_trigger is True and case.assertions == []

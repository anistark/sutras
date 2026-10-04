"""Main CLI entry point for sutras - skill devtool."""

import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from sutras import Skill, SkillLoader, __version__
from sutras.cli.errors import invalid_skill, operation_failed, skill_not_found
from sutras.cli.progress import spinner
from sutras.core.abi import BenchConfig
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
from sutras.core.builder import BuildError, SkillBuilder
from sutras.core.config import SutrasConfig
from sutras.core.docgen import generate_docs, write_docs
from sutras.core.estimator import CostEstimate, anthropic_token_counter, estimate_cost
from sutras.core.evaluator import Evaluator
from sutras.core.installer import SkillInstaller
from sutras.core.judge import Judge
from sutras.core.naming import SkillName
from sutras.core.pricing import (
    DEFAULT_BENCH_MODELS,
    ModelPrice,
    canonical_model_id,
    get_price,
    split_model_spec,
)
from sutras.core.publisher import PublishError, SkillPublisher
from sutras.core.registry import RegistryManager
from sutras.core.runtime import ClaudeCodeExecutor, ModelDiscovery
from sutras.core.semver import Version, VersionRange
from sutras.core.skill import SkillLoadError
from sutras.core.test_runner import TestRunner
from sutras.core.validation import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    extract_file_references,
    is_known_tool,
    parse_tool_entry,
)


def _verbose(ctx: click.Context) -> bool:
    """Get verbose flag from Click context, considering both global and local flags."""
    return ctx.obj.get("verbose", False) if ctx.obj else False


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output for debugging",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """
    Sutras - Devtool for Anthropic Agent Skills.

    Create, evaluate, test, distribute, and discover skills with ease.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command(name="list")
@click.option(
    "--local/--no-local",
    default=True,
    help="Include project skills from .claude/skills/",
)
@click.option(
    "--global/--no-global",
    "global_",
    default=True,
    help="Include global skills from ~/.claude/skills/",
)
@click.pass_context
def list_skills(ctx: click.Context, local: bool, global_: bool) -> None:
    """List available skills."""
    verbose = _verbose(ctx)
    try:
        loader = SkillLoader(include_project=local, include_global=global_)
        if verbose:
            click.echo(click.style("Search paths:", fg="bright_black"))
            for p in loader.search_paths:
                click.echo(click.style(f"  {p}", fg="bright_black"))
            click.echo()
        skills = loader.discover()

        if not skills:
            click.echo(click.style("No skills found.", fg="yellow"))
            click.echo("\nCreate a new skill with: ")
            click.echo(click.style("  sutras new <skill-name>", fg="cyan", bold=True))
            return

        click.echo(click.style(f"Found {len(skills)} skill(s):", fg="green", bold=True))
        click.echo()

        for skill_name in skills:
            try:
                skill = loader.load(skill_name)
                version_str = (
                    f" {click.style(f'v{skill.version}', fg='blue')}" if skill.version else ""
                )
                click.echo(f"  {click.style(skill.name, fg='cyan', bold=True)}{version_str}")

                desc = skill.description
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                click.echo(f"    {desc}")

                if skill.path:
                    click.echo(click.style(f"    {skill.path}", fg="bright_black"))
                click.echo()
            except Exception as e:
                failed_name = click.style(skill_name, fg="red")
                failed_msg = click.style("(failed to load)", fg="yellow")
                click.echo(f"  {failed_name} {failed_msg}")
                click.echo(click.style(f"    Error: {str(e)}", fg="red"))
                click.echo()
    except Exception as e:
        click.echo(click.style(f"Error listing skills: {str(e)}", fg="red"), err=True)
        raise click.Abort()


@cli.command()
@click.argument("name")
def info(name: str) -> None:
    """Show detailed information about a skill."""
    loader = SkillLoader()

    try:
        skill = loader.load(name)

        click.echo(click.style("═" * 60, fg="blue"))
        click.echo(click.style(f"  {skill.name}", fg="cyan", bold=True))
        if skill.version:
            click.echo(click.style(f"  Version: {skill.version}", fg="blue"))
        click.echo(click.style("═" * 60, fg="blue"))
        click.echo()

        click.echo(click.style("Description:", fg="green", bold=True))
        click.echo(f"  {skill.description}")
        click.echo()

        click.echo(click.style("Location:", fg="green", bold=True))
        click.echo(click.style(f"  {skill.path}", fg="bright_black"))
        click.echo()

        if skill.author:
            click.echo(click.style("Author:", fg="green", bold=True))
            click.echo(f"  {skill.author}")
            click.echo()

        if skill.allowed_tools:
            click.echo(click.style("Allowed Tools:", fg="green", bold=True))
            click.echo(f"  {', '.join(skill.allowed_tools)}")
            click.echo()

        if skill.abi:
            if skill.abi.license:
                click.echo(click.style("License:", fg="green", bold=True))
                click.echo(f"  {skill.abi.license}")
                click.echo()

            if skill.abi.repository:
                click.echo(click.style("Repository:", fg="green", bold=True))
                click.echo(f"  {skill.abi.repository}")
                click.echo()

            if skill.abi.distribution:
                if skill.abi.distribution.tags:
                    click.echo(click.style("Tags:", fg="green", bold=True))
                    tags = ", ".join(skill.abi.distribution.tags)
                    click.echo(f"  {tags}")
                    click.echo()

                if skill.abi.distribution.category:
                    click.echo(click.style("Category:", fg="green", bold=True))
                    click.echo(f"  {skill.abi.distribution.category}")
                    click.echo()

        if skill.supporting_files:
            click.echo(click.style("Supporting Files:", fg="green", bold=True))
            for filename in sorted(skill.supporting_files.keys()):
                click.echo(f"  • {filename}")
            click.echo()

        if skill.abi and skill.abi.compatibility:
            stale = skill.abi.compatibility.skill_hash != compute_skill_hash(skill)
            _print_compatibility(skill.abi.compatibility.model_dump(), stale=stale)

    except FileNotFoundError as e:
        if name.startswith("@") and _print_registry_info(name):
            return
        skill_not_found(name, str(e))
    except ValueError as e:
        invalid_skill(name, str(e))
    except Exception as e:
        operation_failed("Loading skill", str(e))


@cli.command()
@click.argument("name", required=False)
@click.option(
    "--description",
    "-d",
    help="Skill description (what it does and when to use it)",
)
@click.option(
    "--author",
    "-a",
    help="Skill author name",
)
@click.option(
    "--template",
    "-t",
    default="default",
    help="Template to use (run with --list-templates to see options)",
)
@click.option(
    "--list-templates",
    is_flag=True,
    help="List available skill templates",
)
@click.option(
    "--global",
    "global_",
    is_flag=True,
    help="Create in global skills directory (~/.claude/skills/)",
)
def new(
    name: str | None,
    description: str | None,
    author: str | None,
    template: str,
    list_templates: bool,
    global_: bool,
) -> None:
    """Create a new skill with proper structure.

    Use --template to start from a specialized template:

    \b
      sutras new my-skill --template code-review
      sutras new my-api --template api-integration

    Use --list-templates to see all available templates.
    """
    from sutras.core import templates as _templates

    if list_templates:
        templates = _templates.list_templates()
        click.echo(click.style(f"Available templates ({len(templates)}):", fg="green", bold=True))
        click.echo()
        for tmpl in templates:
            click.echo(f"  {click.style(tmpl.name, fg='cyan', bold=True)}")
            click.echo(f"    {tmpl.description}")
            click.echo()
        click.echo(click.style("Usage:", fg="yellow", bold=True))
        click.echo(click.style("  sutras new <name> --template <template>", fg="cyan"))
        return

    if not name:
        click.echo(click.style("✗ ", fg="red") + "Skill name is required", err=True)
        click.echo("\nUsage: sutras new <name> [OPTIONS]")
        raise click.Abort()

    if not name.replace("-", "").replace("_", "").isalnum():
        click.echo(
            click.style("✗ ", fg="red")
            + "Skill name must contain only alphanumeric characters, hyphens, and underscores",
            err=True,
        )
        raise click.Abort()

    name = name.lower()

    try:
        tmpl = _templates.get_template(template)
    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + str(e), err=True)
        click.echo(f"\nRun {click.style('sutras new --list-templates', fg='cyan')} to see options")
        raise click.Abort()

    if global_:
        skills_dir = Path.home() / ".claude" / "skills"
    else:
        skills_dir = Path.cwd() / ".claude" / "skills"

    skill_dir = skills_dir / name

    if skill_dir.exists():
        click.echo(
            click.style("✗ ", fg="red") + f"Skill '{name}' already exists at {skill_dir}", err=True
        )
        raise click.Abort()

    description = description or f"Description of {name} skill"
    author = author or "Skill Author"

    rendered = _templates.render_template(tmpl, name, description, author)

    click.echo(click.style(f"Creating skill: {name}", fg="cyan", bold=True))
    if template != "default":
        click.echo(click.style(f"  Template: {template}", fg="blue"))
    click.echo()

    skill_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in sorted(rendered.items()):
        (skill_dir / filename).write_text(content)
        click.echo(click.style("✓ ", fg="green") + f"Created {filename}")

    click.echo()
    click.echo(click.style("✓ Success!", fg="green", bold=True) + " Skill created at:")
    click.echo(click.style(f"  {skill_dir}", fg="cyan"))
    click.echo()
    click.echo(click.style("Next steps:", fg="yellow", bold=True))
    click.echo(f"  1. Edit {click.style('SKILL.md', fg='cyan')} to define your skill")
    click.echo(f"  2. Update {click.style('sutras.yaml', fg='cyan')} with metadata")
    click.echo(f"  3. Run: {click.style(f'sutras info {name}', fg='green')}")
    click.echo(f"  4. Validate: {click.style(f'sutras validate {name}', fg='green')}")
    click.echo("  5. Test your skill with Claude")


@cli.command()
@click.argument("name")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose test output",
)
@click.option(
    "--fail-fast",
    "-x",
    is_flag=True,
    help="Stop on first test failure",
)
@click.pass_context
def test(ctx: click.Context, name: str, verbose: bool, fail_fast: bool) -> None:
    """Run tests for a skill."""
    verbose = verbose or _verbose(ctx)
    loader = SkillLoader()

    try:
        click.echo(click.style(f"Running tests for: {name}", fg="cyan", bold=True))
        click.echo()

        skill = loader.load(name)

        if not skill.abi or not skill.abi.tests or not skill.abi.tests.cases:
            click.echo(click.style("⚠ No tests found", fg="yellow"))
            click.echo()
            click.echo("Add tests to sutras.yaml:")
            click.echo(
                click.style(
                    """
tests:
  cases:
    - name: "basic-test"
      inputs:
        example: "value"
      expected:
        status: "success"
""",
                    fg="bright_black",
                )
            )
            return

        runner = TestRunner(skill)

        if verbose:
            click.echo(click.style("Test configuration:", fg="blue"))
            click.echo(f"  Fixtures dir: {skill.abi.tests.fixtures_dir or 'none'}")
            click.echo(f"  Test cases: {len(skill.abi.tests.cases)}")
            if skill.abi.tests.coverage_threshold:
                click.echo(f"  Coverage threshold: {skill.abi.tests.coverage_threshold}%")
            click.echo()

        summary = runner.run(verbose=verbose)

        if not summary.results:
            click.echo(click.style("⚠ No test results", fg="yellow"))
            return

        for result in summary.results:
            if result.passed:
                click.echo(click.style("✓", fg="green") + f" {result.name}")
                if verbose and result.message:
                    click.echo(click.style(f"    {result.message}", fg="bright_black"))
            else:
                click.echo(click.style("✗", fg="red") + f" {result.name}")
                if result.message:
                    click.echo(click.style(f"    {result.message}", fg="red"))
                if verbose:
                    if result.expected:
                        click.echo(click.style(f"    Expected: {result.expected}", fg="yellow"))
                    if result.actual:
                        click.echo(click.style(f"    Actual: {result.actual}", fg="yellow"))

            if fail_fast and not result.passed:
                click.echo()
                click.echo(click.style("Stopping on first failure (--fail-fast)", fg="yellow"))
                break

        click.echo()
        click.echo(click.style("─" * 60, fg="blue"))

        if summary.success:
            click.echo(
                click.style("✓ ", fg="green", bold=True)
                + click.style(f"{summary.passed}/{summary.total} tests passed", fg="green")
            )
        else:
            click.echo(
                click.style("✗ ", fg="red", bold=True)
                + click.style(f"{summary.failed}/{summary.total} tests failed", fg="red")
            )

        if skill.abi.tests.coverage_threshold and summary.total > 0:
            pass_rate = (summary.passed / summary.total) * 100
            threshold = skill.abi.tests.coverage_threshold
            if pass_rate >= threshold:
                click.echo(
                    click.style(
                        f"✓ Coverage threshold met: {pass_rate:.1f}% >= {threshold}%", fg="green"
                    )
                )
            else:
                click.echo(
                    click.style(
                        f"✗ Coverage threshold not met: {pass_rate:.1f}% < {threshold}%", fg="red"
                    )
                )

        if not summary.success:
            raise click.Abort()

    except FileNotFoundError as e:
        skill_not_found(name, str(e))
    except Exception as e:
        operation_failed("Running tests", str(e))


@cli.command()
@click.argument("name")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose evaluation output",
)
@click.option(
    "--no-history",
    is_flag=True,
    help="Don't save evaluation results to history",
)
@click.option(
    "--show-history",
    is_flag=True,
    help="Show evaluation history for this skill",
)
@click.pass_context
def eval(
    ctx: click.Context, name: str, verbose: bool, no_history: bool, show_history: bool
) -> None:
    """Evaluate a skill using configured metrics."""
    verbose = verbose or _verbose(ctx)
    loader = SkillLoader()

    try:
        skill = loader.load(name)

        if show_history:
            evaluator = Evaluator(skill)
            history_files = evaluator.history.list(skill_name=name)

            if not history_files:
                click.echo(click.style("No evaluation history found", fg="yellow"))
                return

            click.echo(click.style(f"Evaluation history for: {name}", fg="cyan", bold=True))
            click.echo()

            for filepath in history_files[:10]:
                history_data = evaluator.history.load(filepath)
                timestamp = datetime.fromisoformat(history_data["timestamp"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                passed = history_data["passed"]
                total = history_data["total"]
                status = (
                    click.style("✓", fg="green") if passed == total else click.style("✗", fg="red")
                )

                click.echo(f"{status} {timestamp} - {passed}/{total} passed")

                if verbose and history_data.get("metrics"):
                    for metric_name, score in history_data["metrics"].items():
                        click.echo(
                            click.style(f"    {metric_name}: {score:.3f}", fg="bright_black")
                        )

            return

        click.echo(click.style(f"Running evaluation for: {name}", fg="cyan", bold=True))
        click.echo()

        if not skill.abi or not skill.abi.eval:
            click.echo(click.style("⚠ No evaluation configuration found", fg="yellow"))
            click.echo()
            click.echo("Add evaluation config to sutras.yaml:")
            click.echo(
                click.style(
                    """
eval:
  framework: "ragas"
  metrics: ["faithfulness", "answer_relevancy"]
  dataset: "tests/eval/dataset.json"
  threshold: 0.7
""",
                    fg="bright_black",
                )
            )
            return

        evaluator = Evaluator(skill)

        if verbose:
            click.echo(click.style("Evaluation configuration:", fg="blue"))
            click.echo(f"  Framework: {skill.abi.eval.framework}")
            click.echo(f"  Metrics: {', '.join(skill.abi.eval.metrics)}")
            if skill.abi.eval.dataset:
                click.echo(f"  Dataset: {skill.abi.eval.dataset}")
            if skill.abi.eval.threshold:
                click.echo(f"  Threshold: {skill.abi.eval.threshold}")
            click.echo()

        try:
            with spinner("Running evaluation"):
                summary = evaluator.run(save_history=not no_history)
        except ImportError as e:
            click.echo(click.style("✗ ", fg="red") + str(e), err=True)
            click.echo()
            click.echo("Install evaluation dependencies:")
            click.echo(click.style("  pip install ragas", fg="cyan"))
            raise click.Abort()

        if not summary.results:
            click.echo(click.style("⚠ No evaluation results", fg="yellow"))
            return

        for result in summary.results:
            if result.passed:
                click.echo(click.style("✓", fg="green") + f" {result.name}")
            else:
                click.echo(click.style("✗", fg="red") + f" {result.name}")

            if verbose or not result.passed:
                for metric_name, score in result.metrics.items():
                    color = "green" if score >= 0.7 else "yellow" if score >= 0.5 else "red"
                    click.echo(click.style(f"    {metric_name}: {score:.3f}", fg=color))

                if result.message and not result.passed:
                    click.echo(click.style(f"    {result.message}", fg="red"))

        click.echo()
        click.echo(click.style("─" * 60, fg="blue"))

        click.echo(click.style("Average Metrics:", fg="cyan", bold=True))
        for metric_name, score in summary.metrics.items():
            color = "green" if score >= 0.7 else "yellow" if score >= 0.5 else "red"
            click.echo(click.style(f"  {metric_name}: {score:.3f}", fg=color))

        click.echo()

        if summary.success:
            click.echo(
                click.style("✓ ", fg="green", bold=True)
                + click.style(f"{summary.passed}/{summary.total} cases passed", fg="green")
            )
        else:
            click.echo(
                click.style("✗ ", fg="red", bold=True)
                + click.style(f"{summary.failed}/{summary.total} cases failed", fg="red")
            )

        if skill.abi.eval.threshold:
            avg_score = (
                sum(summary.metrics.values()) / len(summary.metrics) if summary.metrics else 0.0
            )
            threshold = skill.abi.eval.threshold
            if avg_score >= threshold:
                click.echo(
                    click.style(f"✓ Threshold met: {avg_score:.3f} >= {threshold}", fg="green")
                )
            else:
                click.echo(
                    click.style(f"✗ Threshold not met: {avg_score:.3f} < {threshold}", fg="red")
                )

        if not no_history:
            click.echo()
            click.echo(
                click.style("History saved to: ", fg="bright_black")
                + click.style(f"{skill.path}/.sutras/eval_history/", fg="cyan")
            )

        if not summary.success:
            raise click.Abort()

    except FileNotFoundError as e:
        skill_not_found(name, str(e))
    except ValueError as e:
        operation_failed(
            "Evaluation config",
            str(e),
            [
                "Check the 'eval' section in sutras.yaml",
                f"Run {click.style(f'sutras validate {name}', fg='cyan')} to check skill structure",
            ],
        )
    except Exception as e:
        operation_failed("Running evaluation", str(e))


def _print_compatibility(compat: dict[str, Any], stale: bool = False) -> None:
    """Print a "Tested on" block from a compatibility record (as a dict)."""
    header = f"Tested on ({compat.get('runtime', 'unknown')}, {compat.get('benched_at', '?')}):"
    click.echo(click.style(header, fg="green", bold=True))
    for model, result in (compat.get("results") or {}).items():
        mark = (
            click.style("✗", fg="red") if result.get("regression") else click.style("✓", fg="green")
        )
        baseline = " (baseline)" if model == compat.get("baseline") else ""
        click.echo(
            f"  {mark} {model}{baseline}: {result.get('pass_rate', 0):.0%} pass, "
            f"{result.get('trigger_rate', 0):.0%} trigger, {result.get('runs', 0)} runs"
        )
    click.echo(click.style("  Author-reported results from `sutras bench`", fg="bright_black"))
    if stale:
        click.echo(click.style("  ⚠ Stale: the skill changed since these results", fg="yellow"))
    click.echo()


def _print_registry_info(name: str) -> bool:
    """Show a registry entry for a skill that isn't installed locally."""
    try:
        registry_name, entry = RegistryManager().find_skill(name)
    except Exception:
        return False

    click.echo(click.style("═" * 60, fg="blue"))
    click.echo(click.style(f"  {entry.name}", fg="cyan", bold=True))
    click.echo(click.style(f"  Version: {entry.version} · registry: {registry_name}", fg="blue"))
    click.echo(click.style("═" * 60, fg="blue"))
    click.echo()
    if entry.description:
        click.echo(click.style("Description:", fg="green", bold=True))
        click.echo(f"  {entry.description}")
        click.echo()
    if entry.author:
        click.echo(click.style("Author:", fg="green", bold=True))
        click.echo(f"  {entry.author}")
        click.echo()
    if entry.compatibility:
        _print_compatibility(entry.compatibility)
    click.echo(
        click.style(f"Not installed. Install with: sutras install {name}", fg="bright_black")
    )
    return True


def _skill_loader(skills_path: Path | None) -> SkillLoader:
    """Loader limited to ``skills_path`` when given, else the default search paths."""
    if skills_path:
        return SkillLoader(search_paths=[skills_path], include_global=False, include_project=False)
    return SkillLoader()


def _resolve_skill_path(target: str, loader: SkillLoader) -> Path:
    """Resolve a skill name or a path to a skill directory; aborts if not found."""
    target_path = Path(target)
    if target_path.is_dir() and (target_path / "SKILL.md").exists():
        return target_path
    path = loader.find_path(target)
    if path is None:
        searched = ", ".join(str(p) for p in loader.search_paths) or "(none)"
        skill_not_found(target, f"Searched: {searched}")
        raise click.Abort()
    return path


def _is_valid_semver(version: str) -> bool:
    """Check that a version string is canonical semver (MAJOR.MINOR.PATCH[-prerelease])."""
    try:
        return str(Version.parse(version)) == version
    except ValueError:
        return False


def _print_validation_summary(
    name: str,
    errors: list[tuple[str, str, str | None]],
    warnings: list[tuple[str, str, str | None]],
    strict: bool,
) -> None:
    """Print the per-skill error/warning list and the final status line."""
    click.echo(click.style("─" * 50, fg="blue"))

    if errors:
        click.echo(click.style(f"Errors ({len(errors)}):", fg="red", bold=True))
        for category, msg, fix in errors:
            click.echo(click.style(f"  ✗ [{category}] ", fg="red") + msg)
            if fix:
                click.echo(click.style(f"    Fix: {fix}", fg="bright_black"))
        click.echo()

    if warnings:
        click.echo(click.style(f"Warnings ({len(warnings)}):", fg="yellow", bold=True))
        for category, msg, fix in warnings:
            click.echo(click.style(f"  ⚠ [{category}] ", fg="yellow") + msg)
            if fix:
                click.echo(click.style(f"    Fix: {fix}", fg="bright_black"))
        click.echo()

    if errors:
        click.echo(
            click.style("✗ ", fg="red", bold=True)
            + click.style(f"Skill '{name}' has errors", fg="red")
        )
    elif strict and warnings:
        click.echo(
            click.style("✗ ", fg="red", bold=True)
            + click.style(f"Skill '{name}' has warnings (strict mode)", fg="red")
        )
    else:
        status_parts = []
        if not warnings:
            status_parts.append("no issues found")
        else:
            status_parts.append(f"{len(warnings)} warning(s)")
        click.echo(
            click.style("✓ ", fg="green", bold=True)
            + click.style(f"Skill '{name}' is valid", fg="green")
            + f" ({', '.join(status_parts)})"
        )


def _report_load_failure(
    label: str, path: Path, error: SkillLoadError, verbose: bool, strict: bool
) -> tuple[int, int]:
    """Report a skill whose SKILL.md or sutras.yaml could not be parsed.

    Each parse problem is reported as a separate error so broken skills show
    up in the same report format as other validation failures.

    Returns (error_count, warning_count).
    """
    click.echo(click.style(f"Validating skill: {label}", fg="cyan", bold=True))
    click.echo()

    if verbose:
        click.echo(click.style("  Path:", fg="bright_black") + f" {path}")
        click.echo()

    if error.file == "SKILL.md":
        section, category = "Structure", "structure"
        hint = "SKILL.md must start with YAML frontmatter containing 'name' and 'description'"
    else:
        section, category = f"ABI ({error.file})", "abi"
        hint = (
            f"{error.file} must be a YAML mapping matching the Sutras ABI ('version' is required)"
        )

    click.echo(click.style(section, fg="blue", bold=True))
    click.echo(click.style("  ✗", fg="red") + f" {error.file} could not be parsed")
    click.echo(click.style(f"    {hint}", fg="bright_black"))
    click.echo()

    errors: list[tuple[str, str, str | None]] = [(category, p, None) for p in error.problems]
    _print_validation_summary(label, errors, [], strict)
    return len(errors), 0


def _run_validation_checks(skill: Skill, verbose: bool, strict: bool) -> tuple[int, int]:
    """Run all validation checks on a skill and print results.

    Returns (error_count, warning_count). Does not raise on validation
    failure — callers decide whether to abort.
    """
    import os
    import re

    warnings: list[tuple[str, str, str | None]] = []  # (category, message, fix)
    errors: list[tuple[str, str, str | None]] = []  # (category, message, fix)

    def _ok(msg: str) -> None:
        click.echo(click.style("  ✓", fg="green") + f" {msg}")

    def _warn(category: str, msg: str, fix: str | None = None) -> None:
        warnings.append((category, msg, fix))

    def _err(category: str, msg: str, fix: str | None = None) -> None:
        errors.append((category, msg, fix))

    def _check_tool_entries(entries: list[str], field: str, category: str) -> None:
        for entry in entries:
            if not entry.strip():
                continue
            base = parse_tool_entry(entry)
            if base is None:
                _warn(
                    category,
                    f"Malformed {field} entry '{entry}'",
                    "Use 'ToolName' or 'ToolName(pattern)', separated by commas",
                )
            elif not is_known_tool(base):
                _warn(
                    category,
                    f"Unknown tool '{base}' in {field}",
                    "Check spelling against Claude Code tool names (e.g. Read, Write, Bash)",
                )

    click.echo(click.style(f"Validating skill: {skill.name or '(unnamed)'}", fg="cyan", bold=True))
    click.echo()

    if verbose:
        click.echo(click.style("  Path:", fg="bright_black") + f" {skill.path}")
        click.echo()

    # --- Structure checks ---
    click.echo(click.style("Structure", fg="blue", bold=True))

    _ok("SKILL.md found and parsed")

    if not skill.name:
        _err(
            "structure",
            "Missing 'name' in SKILL.md frontmatter",
            "Add 'name: my-skill' to the YAML frontmatter",
        )
    else:
        try:
            bare_name = SkillName.parse(skill.name).name
        except ValueError:
            bare_name = skill.name

        if not re.match(r"^[a-z0-9][a-z0-9._-]*$", bare_name):
            _warn(
                "structure",
                f"Name '{skill.name}' uses non-standard characters",
                "Use lowercase alphanumeric, hyphens, underscores",
            )
        if len(skill.name) > MAX_NAME_LENGTH:
            _err(
                "structure",
                f"Name is {len(skill.name)} chars (max {MAX_NAME_LENGTH})",
                f"Shorten the name to {MAX_NAME_LENGTH} characters or fewer",
            )

        dir_name = skill.path.absolute().name
        if dir_name != bare_name:
            _warn(
                "structure",
                f"Name '{bare_name}' does not match directory name '{dir_name}'",
                f"Rename the directory to '{bare_name}' or update 'name' in SKILL.md",
            )
        _ok(f"Name: {click.style(skill.name, fg='cyan')}")

    if not skill.description:
        _err(
            "structure",
            "Missing 'description' in SKILL.md frontmatter",
            "Add 'description: ...' to the YAML frontmatter",
        )
    else:
        desc_len = len(skill.description)
        if desc_len > MAX_DESCRIPTION_LENGTH:
            _err(
                "structure",
                f"Description is {desc_len} chars (max {MAX_DESCRIPTION_LENGTH})",
                "Shorten the description and move detail into the instructions body",
            )
        elif desc_len < 20:
            _warn(
                "structure",
                f"Description very short ({desc_len} chars)",
                "Write 20+ chars for Claude to understand the skill",
            )
        elif desc_len < 50:
            _warn(
                "structure",
                f"Description is short ({desc_len} chars)",
                "Recommend 50+ chars for better Claude discovery",
            )
        _ok(f"Description ({desc_len} chars)")

    if not skill.instructions or len(skill.instructions.strip()) < 10:
        _warn(
            "structure",
            "SKILL.md instructions body is empty or very short",
            "Add detailed instructions after the frontmatter",
        )

    if skill.allowed_tools:
        _ok(f"Allowed tools: {', '.join(skill.allowed_tools)}")
        _check_tool_entries(skill.allowed_tools, "allowed-tools", "structure")

    if skill.supporting_files:
        _ok(f"{len(skill.supporting_files)} supporting file(s)")

    click.echo()

    # --- ABI checks ---
    click.echo(click.style("ABI (sutras.yaml)", fg="blue", bold=True))

    if skill.abi:
        _ok("sutras.yaml found and parsed")

        if _is_valid_semver(skill.abi.version):
            _ok(f"Version: {click.style(skill.abi.version, fg='blue')}")
        else:
            _err(
                "abi",
                f"Version '{skill.abi.version}' is not valid semver",
                "Use format: MAJOR.MINOR.PATCH[-prerelease] (e.g., 1.0.0, 1.0.0-beta.1)",
            )

        if not skill.abi.author:
            _warn(
                "abi",
                "Missing 'author' field",
                "Add 'author: \"Your Name\"' to sutras.yaml",
            )
        else:
            _ok(f"Author: {skill.abi.author}")

        if "license" not in skill.abi.model_fields_set or not skill.abi.license:
            _warn(
                "abi",
                "Missing 'license' field (defaults to MIT)",
                "Add 'license: \"MIT\"' (or your license) to sutras.yaml",
            )
        else:
            _ok(f"License: {skill.abi.license}")

        if skill.abi.repository:
            _ok(f"Repository: {skill.abi.repository}")

        caps = skill.abi.capabilities
        if caps:
            _check_tool_entries(caps.tools, "capabilities.tools", "abi")

            valid_deps = 0
            for dep in caps.dependencies:
                dep_name, constraint = (
                    (dep, "*") if isinstance(dep, str) else (dep.name, dep.version)
                )
                problems_before = len(errors)
                try:
                    if not SkillName.parse(dep_name).is_scoped:
                        _err(
                            "abi",
                            f"Dependency '{dep_name}' is not scoped and can't be resolved "
                            "from a registry",
                            "Use '@namespace/skill-name'",
                        )
                except ValueError as e:
                    _err("abi", f"Invalid dependency name: {e}", "Use '@namespace/skill-name'")
                try:
                    VersionRange.parse(constraint)
                except ValueError:
                    _err(
                        "abi",
                        f"Invalid version constraint '{constraint}' for dependency '{dep_name}'",
                        "Use npm-style constraints: ^1.0.0, ~1.2.3, >=1.0.0 <2.0.0, 1.x, *",
                    )
                if len(errors) == problems_before:
                    valid_deps += 1
            if valid_deps:
                _ok(f"{valid_deps} valid dependenc{'y' if valid_deps == 1 else 'ies'}")
    else:
        _warn(
            "abi",
            "No sutras.yaml found",
            "Create sutras.yaml for version, testing, and distribution",
        )

    click.echo()

    # --- Distribution readiness ---
    click.echo(click.style("Distribution", fg="blue", bold=True))

    if skill.abi and skill.abi.distribution:
        dist = skill.abi.distribution
        if dist.tags:
            _ok(f"Tags: {', '.join(dist.tags)}")
        else:
            _warn(
                "distribution",
                "No tags specified",
                "Add tags for better skill discoverability",
            )

        if dist.category:
            _ok(f"Category: {dist.category}")
        else:
            _warn(
                "distribution",
                "No category specified",
                "Add a category to help organize the skill",
            )

        if dist.homepage:
            _ok(f"Homepage: {dist.homepage}")
        if dist.keywords:
            _ok(f"Keywords: {', '.join(dist.keywords)}")
    elif skill.abi:
        _warn(
            "distribution",
            "No distribution metadata",
            "Add a 'distribution' section with tags and category",
        )
    else:
        click.echo(click.style("  ·", fg="bright_black") + " Skipped (no sutras.yaml)")

    click.echo()

    # --- File references ---
    file_refs = extract_file_references(skill.instructions)
    tests_cfg = skill.abi.tests if skill.abi else None
    fixtures_dir = (
        tests_cfg.fixtures_dir
        if tests_cfg and "fixtures_dir" in tests_cfg.model_fields_set
        else None
    )
    dataset = skill.abi.eval.dataset if skill.abi and skill.abi.eval else None

    if file_refs or fixtures_dir or dataset:
        click.echo(click.style("Files", fg="blue", bold=True))

        packaged = set(skill.supporting_files) | {"SKILL.md", "sutras.yaml"}
        found_refs = 0
        for ref in file_refs:
            rel = Path(os.path.normpath(ref))
            if not (skill.path / rel).exists():
                _err(
                    "files",
                    f"SKILL.md links to missing file '{ref}'",
                    "Create the file or fix the link",
                )
            elif rel.parts[:1] == ("..",):
                _warn(
                    "files",
                    f"SKILL.md links to '{ref}', outside the skill directory",
                    "Move it into the skill directory so it ships with the skill",
                )
            elif len(rel.parts) > 1 or rel.name not in packaged:
                _warn(
                    "files",
                    f"SKILL.md links to '{ref}', which `sutras build` won't package",
                    "Only top-level files are packaged; move it to the skill's root directory",
                )
            else:
                found_refs += 1
        if found_refs:
            _ok(f"{found_refs} linked file(s) found")

        if fixtures_dir:
            if (skill.path / fixtures_dir).is_dir():
                _ok(f"Fixtures directory: {fixtures_dir}")
            else:
                _warn(
                    "testing",
                    f"tests.fixtures_dir '{fixtures_dir}' does not exist",
                    "Create the directory or remove 'fixtures_dir' from sutras.yaml",
                )

        if dataset:
            if (skill.path / dataset).is_file():
                _ok(f"Eval dataset: {dataset}")
            else:
                _err(
                    "eval",
                    f"eval.dataset '{dataset}' not found",
                    "Create the dataset file or fix the path in sutras.yaml",
                )

        click.echo()

    # --- Bench config and recorded results ---
    bench_cfg = skill.abi.bench if skill.abi else None
    compat = skill.abi.compatibility if skill.abi else None
    if bench_cfg or compat:
        click.echo(click.style("Bench", fg="blue", bold=True))

    if bench_cfg:
        names = [c.name for c in bench_cfg.cases]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            _err(
                "bench",
                f"Duplicate case name(s): {', '.join(duplicates)}",
                "Give each case a unique name",
            )
        for spec in [*bench_cfg.models, bench_cfg.baseline, bench_cfg.judge]:
            if not spec:
                continue
            try:
                split_model_spec(spec)
            except ValueError as e:
                _err("bench", str(e), "Use 'model' or 'model@effort'")
        for case in bench_cfg.cases:
            if case.workspace and not (skill.path / case.workspace).is_dir():
                _err(
                    "bench",
                    f"Case '{case.name}' workspace '{case.workspace}' not found",
                    "Create the directory or fix 'workspace' in sutras.yaml",
                )
        if bench_cfg.cases:
            _ok(f"{len(bench_cfg.cases)} bench case(s)")
        else:
            _warn("bench", "Bench section has no cases", "Add cases under 'bench.cases'")

    if compat:
        if compat.skill_hash != compute_skill_hash(skill):
            _warn(
                "bench",
                f"Recorded bench results are stale (skill changed since {compat.benched_at})",
                "Re-run `sutras bench` then `sutras bench --record`",
            )
        else:
            tested = ", ".join(
                f"{model} {result.pass_rate:.0%}" for model, result in compat.results.items()
            )
            _ok(f"Tested on: {tested}")

    if bench_cfg or compat:
        click.echo()

    # --- Testing config ---
    if verbose:
        click.echo(click.style("Testing", fg="blue", bold=True))
        if skill.abi and skill.abi.tests and skill.abi.tests.cases:
            _ok(f"{len(skill.abi.tests.cases)} test case(s) defined")
        else:
            _warn(
                "testing",
                "No test cases defined",
                "Add test cases in the 'tests' section of sutras.yaml",
            )
        click.echo()

    _print_validation_summary(skill.name, errors, warnings, strict)

    return len(errors), len(warnings)


@cli.command()
@click.argument("target", required=False, metavar="[NAME|PATH]")
@click.option(
    "--all",
    "all_",
    is_flag=True,
    help="Validate all skills discovered in the skills directory",
)
@click.option(
    "--path",
    "skills_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Skills directory to search (for --all), or a custom search path for a named skill",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict validation (warnings become errors)",
)
@click.pass_context
def validate(
    ctx: click.Context,
    target: str | None,
    all_: bool,
    skills_path: Path | None,
    strict: bool,
) -> None:
    """Validate a skill's structure and metadata.

    Accepts a skill name, a path to a skill directory, or --all to validate
    every discovered skill. Checks SKILL.md structure and spec limits, allowed
    tools, sutras.yaml schema, version and dependency constraints, linked
    files, eval/test paths, and distribution readiness.

    \b
    Examples:
      sutras validate my-skill
      sutras validate skills/my-skill
      sutras validate --all
      sutras validate --all --path skills/
      sutras validate my-skill --strict
    """
    verbose = _verbose(ctx)

    loader = _skill_loader(skills_path)
    targets: list[tuple[str, Path]] = []

    if all_:
        if target:
            raise click.UsageError("Cannot combine --all with a skill name or path")
        for name in loader.discover():
            path = loader.find_path(name)
            if path:
                targets.append((name, path))
        if not targets:
            click.echo(click.style("No skills found to validate.", fg="yellow", bold=True))
            return
    elif target:
        path = _resolve_skill_path(target, loader)
        label = path.absolute().name if Path(target).is_dir() else target
        targets.append((label, path))
    else:
        raise click.UsageError("Provide a skill name, a path, or use --all")

    failed: list[str] = []

    for i, (label, path) in enumerate(targets):
        if i > 0:
            click.echo()
        try:
            skill = Skill.load(path)
        except SkillLoadError as e:
            errs, warns = _report_load_failure(label, path, e, verbose, strict)
            display_name = label
        else:
            errs, warns = _run_validation_checks(skill, verbose, strict)
            display_name = skill.name or label
        if errs > 0 or (strict and warns > 0):
            failed.append(display_name)

    if len(targets) > 1:
        click.echo()
        click.echo(click.style("═" * 50, fg="blue"))
        passed = len(targets) - len(failed)
        parts = [click.style(f"{passed} passed", fg="green")]
        if failed:
            parts.append(click.style(f"{len(failed)} failed", fg="red"))
        click.echo(
            click.style(f"Validated {len(targets)} skill(s): ", bold=True) + ", ".join(parts)
        )
        if failed:
            click.echo(click.style("  Failed: ", fg="red") + ", ".join(failed))

    if failed:
        raise click.Abort()


def _split_csv(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _price_label(price: ModelPrice | None) -> str:
    if price is None:
        return "price unknown"
    return f"${price.input:g} / ${price.output:g} per MTok"


def _select_bench_models(
    requested: list[str], config: BenchConfig, discovery: ModelDiscovery
) -> list[str]:
    if requested:
        return requested
    if config.models:
        return list(config.models)
    available = {canonical_model_id(m.id) for m in discovery.models}
    chosen = [m for m in DEFAULT_BENCH_MODELS if m in available]
    return chosen or list(DEFAULT_BENCH_MODELS)


def _print_bench_plan(
    plan: BenchPlan,
    executor: ClaudeCodeExecutor,
    discovery: ModelDiscovery,
    estimate: CostEstimate,
    max_cost: float | None,
    price_of: Callable[[str], ModelPrice | None],
) -> None:
    source = "Models API" if discovery.source == "api" else "Claude Code aliases"
    version = executor.version() or "unknown version"
    click.echo(click.style(f"Bench: {plan.skill.name}", fg="cyan", bold=True))
    click.echo()
    click.echo(f"Runtime:   Claude Code {version} (headless) · models from {source}")

    selected = {canonical_model_id(m) for m in plan.models}
    listed = {canonical_model_id(m.id) for m in discovery.models}
    rows = [(m, True) for m in plan.models]
    rows += [(m.id, False) for m in discovery.models if canonical_model_id(m.id) not in selected]
    width = max(len(m) for m, _ in rows) + 2

    click.echo("Models:")
    for model, chosen in rows:
        box = click.style("[x]", fg="green") if chosen else click.style("[ ]", fg="bright_black")
        notes = []
        if model == plan.baseline:
            notes.append("baseline")
        if chosen and canonical_model_id(model) not in listed:
            notes.append("not listed by runtime")
        suffix = f"   ({', '.join(notes)})" if notes else ""
        click.echo(f"  {box} {model:<{width}} {_price_label(price_of(model))}{suffix}")

    judged = f" + {plan.judged_runs} judge calls ({plan.config.judge})" if plan.judged_runs else ""
    click.echo(
        f"Plan:      {len(plan.cases)} case(s) × {plan.runs} run(s) × {len(plan.models)} model(s)"
        f" = {plan.total_runs} runs{judged}"
    )
    click.echo(
        f"Estimate:  {_usd(estimate.low)} – {_usd(estimate.high)}   "
        + click.style(f"({estimate.method}: {estimate.detail})", fg="bright_black")
    )
    if estimate.unpriced:
        click.echo(
            click.style(
                f"           excludes unpriced: {', '.join(estimate.unpriced)}", fg="yellow"
            )
        )
    if max_cost is not None:
        click.echo(f"Cap:       {_usd(max_cost)} — no run starts if it could exceed the cap")
    else:
        click.echo("Cap:       none " + click.style("(set one with --max-cost)", fg="yellow"))

    if plan.shell_commands:
        click.echo("Commands:  run in the sandbox after each session:")
        for command in plan.shell_commands:
            click.echo(f"             {command}")
    if discovery.note:
        click.echo(click.style(f"Note:      {discovery.note}", fg="bright_black"))
    if discovery.source == "aliases":
        click.echo(
            click.style(
                "           Costs are API-equivalent estimates; on a Claude subscription, runs "
                "draw from your plan's usage limits.",
                fg="bright_black",
            )
        )
    click.echo()


def _record_line(record: RunRecord) -> str:
    mark = click.style("✓", fg="green") if record.passed else click.style("✗", fg="red")
    cost = _usd(record.total_cost) if record.total_cost is not None else "cost unknown"
    line = (
        f"  {mark} {record.model} · {record.case} #{record.run} · {record.num_turns} turns · {cost}"
    )
    if record.passed:
        return line
    if record.error:
        reason = record.error
    elif not record.trigger_ok:
        reason = "skill did not trigger" if not record.triggered else "skill triggered unexpectedly"
    else:
        failed = [a["description"] for a in record.assertions if not a["passed"]]
        failed += [r["criterion"] for r in record.rubric if not r["passed"]]
        reason = "failed: " + "; ".join(failed[:2]) if failed else "failed"
    return line + click.style(f" · {reason}", fg="red")


def _print_bench_summary(report: BenchReport) -> None:
    summaries = report.summaries()
    width = max(len(s.model) for s in summaries) + 2
    click.echo()
    header = f"{'':<{width}}{'trigger':>9}{'pass rate':>12}{'vs baseline':>14}{'cost':>10}"
    click.echo(click.style(header, bold=True))
    for s in summaries:
        if s.delta is None:
            verdict = f"{'—':>10}    "
        else:
            mark = click.style("✗", fg="red") if s.regression else click.style("✓", fg="green")
            verdict = f"{s.delta * 100:>+9.0f}%   {mark}"
        click.echo(
            f"{s.model:<{width}}{f'{s.trigger_ok}/{s.runs}':>9}{s.pass_rate:>12.0%}"
            f"{verdict:>14}{_usd(s.cost_usd):>10}"
        )

    for s in summaries:
        if s.failed_cases:
            cases = ", ".join(f"{c} ({p}/{n})" for c, (p, n) in s.failed_cases.items())
            click.echo(click.style(f"  ✗ {s.model}: failed cases: {cases}", fg="red"))
        if s.untriggered_cases:
            cases = ", ".join(s.untriggered_cases)
            click.echo(click.style(f"  ✗ {s.model}: wrong trigger behavior on: {cases}", fg="red"))

    click.echo()
    spent = f"Spent: {_usd(report.total_cost)}"
    if report.unknown_cost_runs:
        spent += f" (+ {report.unknown_cost_runs} run(s) with unknown cost)"
    click.echo(spent)
    if not report.complete:
        click.echo(click.style(f"Incomplete: {report.stop_reason}", fg="yellow"))


def _print_bench_history(skill: Skill) -> None:
    history = load_history(skill)
    if not history:
        click.echo(click.style(f"No bench history for '{skill.name}'", fg="yellow"))
        return
    click.echo(click.style(f"Bench history for: {skill.name}", fg="cyan", bold=True))
    click.echo()
    for path, report in history[:20]:
        status = "complete" if report.complete else f"incomplete ({report.stop_reason})"
        kind = " [pilot]" if report.kind == "pilot" else ""
        click.echo(f"  {report.started_at}{kind} · {status} · {_usd(report.total_cost)}")
        rates = ", ".join(f"{s.model} {s.pass_rate:.0%}" for s in report.summaries())
        click.echo(click.style(f"    {rates}", fg="bright_black"))
        click.echo(click.style(f"    {path}", fg="bright_black"))


def _record_bench(skill: Skill) -> None:
    report = latest_complete_report(skill)
    if report is None:
        raise click.ClickException(
            f"No complete bench run found for '{skill.name}'. Run `sutras bench` first."
        )
    if report.skill_hash != compute_skill_hash(skill):
        raise click.ClickException(
            f"The skill changed since the last complete bench ({report.started_at}). "
            "Re-run `sutras bench` before recording."
        )
    write_compatibility(skill.path / "sutras.yaml", build_compatibility(report))
    click.echo(
        click.style("✓ ", fg="green", bold=True)
        + f"Recorded results from {report.started_at} in {skill.path / 'sutras.yaml'}"
    )


def _confirm_spend(prompt: str, yes: bool) -> None:
    if yes:
        return
    if not sys.stdin.isatty():
        raise click.UsageError(
            "Approval needed: pass --yes with --max-cost for non-interactive runs"
        )
    if not click.confirm(prompt, default=False):
        raise click.Abort()


@cli.command()
@click.argument("target", metavar="NAME|PATH")
@click.option("--models", help="Comma-separated model IDs or aliases, optionally with @effort")
@click.option("--baseline", help="Model to compare against (default: bench.baseline or first)")
@click.option("--runs", type=click.IntRange(min=1), help="Runs per case per model")
@click.option("--cases", "case_names", help="Comma-separated subset of case names")
@click.option("--max-cost", type=click.FloatRange(min=0, min_open=True), help="Hard cap in USD")
@click.option("--yes", "-y", is_flag=True, help="Skip the approval prompt (requires --max-cost)")
@click.option("--dry-run", is_flag=True, help="Show models, plan, and estimate without running")
@click.option(
    "--pilot", is_flag=True, help="Run one case per model first to calibrate the estimate"
)
@click.option("--record", is_flag=True, help="Write the latest complete run into sutras.yaml")
@click.option(
    "--report",
    "report_format",
    type=click.Choice(["md"]),
    help="Also write a Markdown report (JSON history is always saved)",
)
@click.option("--history", "show_history", is_flag=True, help="List previous bench runs")
@click.option(
    "--parallel", type=click.IntRange(1, 16), default=2, show_default=True, help="Concurrent runs"
)
@click.option("--keep-sandbox", is_flag=True, help="Keep run workspaces for debugging")
@click.option(
    "--path",
    "skills_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Custom skills directory to search for NAME",
)
@click.pass_context
def bench(
    ctx: click.Context,
    target: str,
    models: str | None,
    baseline: str | None,
    runs: int | None,
    case_names: str | None,
    max_cost: float | None,
    yes: bool,
    dry_run: bool,
    pilot: bool,
    record: bool,
    report_format: str | None,
    show_history: bool,
    parallel: int,
    keep_sandbox: bool,
    skills_path: Path | None,
) -> None:
    """Benchmark a skill across models with Claude Code.

    Runs each case in the skill's `bench` section on every selected model in an
    isolated sandbox, grades runs with assertions and an optional rubric judge,
    and compares pass rates against a baseline. Shows available models and an
    estimated cost, and asks for approval before spending anything.

    Exits non-zero when a model regresses past `max_regression` or the run is
    incomplete.

    \b
    Examples:
      sutras bench my-skill --dry-run
      sutras bench my-skill --models opus,sonnet --runs 5 --max-cost 5
      sutras bench my-skill --yes --max-cost 10 --report md
      sutras bench my-skill --history
      sutras bench my-skill --record
    """
    path = _resolve_skill_path(target, _skill_loader(skills_path))
    try:
        skill = Skill.load(path)
    except SkillLoadError as e:
        invalid_skill(target, str(e))
        return

    if show_history:
        _print_bench_history(skill)
        return
    if record:
        _record_bench(skill)
        return

    config = skill.abi.bench if skill.abi else None
    if config is None or not config.cases:
        raise click.ClickException(
            f"Skill '{skill.name}' has no bench cases. Add a 'bench' section with 'cases' "
            "to sutras.yaml."
        )

    executor = ClaudeCodeExecutor()
    if not executor.available():
        raise click.ClickException(
            "Claude Code CLI ('claude') not found on PATH. "
            "Install it from https://code.claude.com/docs"
        )

    selected_cases = config.cases
    if case_names:
        wanted = _split_csv(case_names)
        unknown = [n for n in wanted if n not in {c.name for c in config.cases}]
        if unknown:
            raise click.UsageError(f"Unknown case(s): {', '.join(unknown)}")
        selected_cases = [c for c in config.cases if c.name in wanted]

    overrides = SutrasConfig().get_price_overrides()

    def price_of(model: str) -> ModelPrice | None:
        return get_price(model, overrides)

    with spinner("Discovering models..."):
        discovery = executor.discover_models(overrides)

    model_specs = _select_bench_models(_split_csv(models), config, discovery)
    baseline_spec = baseline or config.baseline or model_specs[0]
    if baseline_spec not in model_specs:
        model_specs.insert(0, baseline_spec)
    for spec in [*model_specs, config.judge]:
        try:
            split_model_spec(spec)
        except ValueError as e:
            raise click.UsageError(str(e))

    plan = BenchPlan(
        skill=skill,
        config=config,
        models=model_specs,
        baseline=baseline_spec,
        cases=selected_cases,
        runs=runs or config.runs,
    )
    cap = max_cost if max_cost is not None else config.max_cost
    if yes and cap is None:
        raise click.UsageError("--yes requires --max-cost (or bench.max_cost in sutras.yaml)")

    judge = Judge(executor, config.judge) if any(c.rubric for c in plan.cases) else None
    counter = anthropic_token_counter()

    def history_reports() -> list[BenchReport]:
        return [r for _, r in load_history(skill)]

    if pilot and not dry_run:
        pilot_plan = plan.pilot()
        pilot_estimate = estimate_cost(pilot_plan, price_of, history_reports(), counter)
        click.echo(
            f"Pilot: {pilot_plan.total_runs} run(s), estimated "
            f"{_usd(pilot_estimate.low)} – {_usd(pilot_estimate.high)}"
        )
        _confirm_spend("Run pilot?", yes)
        pilot_report = BenchRunner(
            pilot_plan,
            executor,
            judge=judge,
            max_cost=cap,
            parallel=parallel,
            keep_sandbox=keep_sandbox,
            reserve_per_run=pilot_estimate.per_run_high,
            on_record=lambda r: click.echo(_record_line(r)),
            sutras_version=__version__,
        ).run(kind="pilot")
        save_report(pilot_report, skill)
        click.echo(f"Pilot spent {_usd(pilot_report.total_cost)}")
        click.echo()
        if cap is not None:
            cap = max(cap - pilot_report.total_cost, 0.01)

    estimate = estimate_cost(plan, price_of, history_reports(), counter)
    _print_bench_plan(plan, executor, discovery, estimate, cap, price_of)
    if dry_run:
        return

    _confirm_spend("Proceed?", yes)
    click.echo()

    report = BenchRunner(
        plan,
        executor,
        judge=judge,
        max_cost=cap,
        parallel=parallel,
        keep_sandbox=keep_sandbox,
        reserve_per_run=estimate.per_run_high,
        on_record=lambda r: click.echo(_record_line(r)),
        sutras_version=__version__,
    ).run()

    _print_bench_summary(report)
    saved = save_report(report, skill)
    click.echo(click.style(f"Saved: {saved}", fg="bright_black"))
    if report_format == "md":
        md_path = saved.with_suffix(".md")
        md_path.write_text(render_markdown(report))
        click.echo(click.style(f"Report: {md_path}", fg="bright_black"))
    if report.complete:
        click.echo(
            "Record results in sutras.yaml: "
            + click.style(f"sutras bench {target} --record", fg="cyan")
        )

    if report.has_regression or not report.complete:
        ctx.exit(1)


@cli.command()
@click.argument("name")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file or directory (default: print to stdout)",
)
@click.option(
    "--no-supporting",
    is_flag=True,
    help="Exclude supporting file contents (examples.md, etc.)",
)
def docs(name: str, output: Path | None, no_supporting: bool) -> None:
    """Generate documentation for a skill.

    Auto-generates a Markdown reference from SKILL.md metadata,
    sutras.yaml ABI, and supporting files.

    \b
    Examples:
      sutras docs my-skill
      sutras docs my-skill -o docs/skills/
      sutras docs my-skill -o my-skill-reference.md
    """
    loader = SkillLoader()

    try:
        skill = loader.load(name)

        include_supporting = not no_supporting

        if output:
            out_path = write_docs(skill, output, include_supporting=include_supporting)
            click.echo(
                click.style("✓ ", fg="green")
                + f"Documentation written to {click.style(str(out_path), fg='cyan')}"
            )
        else:
            content = generate_docs(skill, include_supporting=include_supporting)
            click.echo(content)

    except FileNotFoundError as e:
        skill_not_found(name, str(e))
    except Exception as e:
        operation_failed("Generating docs", str(e))


@cli.command()
@click.argument("name")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for the package (default: ./dist)",
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validation before building",
)
@click.pass_context
def build(ctx: click.Context, name: str, output: Path | None, no_validate: bool) -> None:
    """Build a distributable package for a skill."""
    verbose = _verbose(ctx)
    loader = SkillLoader()

    try:
        click.echo(click.style(f"Building skill: {name}", fg="cyan", bold=True))
        click.echo()

        skill = loader.load(name)

        if verbose:
            click.echo(click.style("Build configuration:", fg="bright_black"))
            click.echo(click.style(f"  Source: {skill.path}", fg="bright_black"))
            click.echo(click.style(f"  Output: {output or './dist'}", fg="bright_black"))
            click.echo(click.style(f"  Validate: {not no_validate}", fg="bright_black"))
            click.echo()

        builder = SkillBuilder(skill, output_dir=output)

        if not no_validate:
            click.echo(click.style("Validating skill...", fg="blue"))
            errors = builder.validate_for_distribution()
            if errors:
                click.echo(click.style("✗ Validation failed:", fg="red", bold=True))
                for error in errors:
                    click.echo(click.style(f"  - {error}", fg="red"))
                click.echo()
                click.echo("Fix the errors and try again, or use --no-validate to skip validation")
                raise click.Abort()
            click.echo(click.style("✓ Validation passed", fg="green"))
            click.echo()

        with spinner("Packaging skill"):
            package_path = builder.build(validate=False)

        package_size = package_path.stat().st_size
        size_str = f"{package_size:,} bytes"
        if package_size > 1024:
            size_str = f"{package_size / 1024:.1f} KB"
        if package_size > 1024 * 1024:
            size_str = f"{package_size / (1024 * 1024):.1f} MB"

        click.echo()
        click.echo(click.style("✓ Build complete!", fg="green", bold=True))
        click.echo()
        click.echo(click.style("Package:", fg="cyan", bold=True))
        click.echo(f"  {package_path}")
        click.echo(click.style(f"  Size: {size_str}", fg="bright_black"))
        click.echo()

        version = skill.abi.version if skill.abi else "0.0.0"
        click.echo(click.style("Package contents:", fg="cyan", bold=True))
        click.echo(f"  Name: {skill.name}")
        click.echo(f"  Version: {version}")
        if skill.abi and skill.abi.author:
            click.echo(f"  Author: {skill.abi.author}")
        click.echo(f"  Files: {len(builder.create_manifest()['files']) + 1}")
        click.echo()

        click.echo(click.style("Next steps:", fg="yellow", bold=True))
        click.echo("  - Test the package by extracting it")
        click.echo("  - Share the package with others")
        click.echo("  - Publish to a skill registry (coming soon)")

    except FileNotFoundError as e:
        skill_not_found(name, str(e))
    except BuildError as e:
        operation_failed(
            "Build",
            str(e),
            [
                "Fix the errors above and try again",
                f"Use {click.style('--no-validate', fg='cyan')} to skip validation",
            ],
        )
    except Exception as e:
        operation_failed("Building skill", str(e))


@cli.group()
def registry() -> None:
    """Manage skill registries."""
    pass


@registry.command("add")
@click.argument("name")
@click.argument("url")
@click.option("--namespace", "-n", help="Default namespace for this registry")
@click.option("--auth-token", "-t", help="Authentication token")
@click.option("--priority", "-p", default=0, help="Registry priority (higher = checked first)")
@click.option("--default", "set_default", is_flag=True, help="Set as default registry")
def registry_add(
    name: str,
    url: str,
    namespace: str | None,
    auth_token: str | None,
    priority: int,
    set_default: bool,
) -> None:
    """Add a new registry."""
    try:
        config = SutrasConfig()
        config.add_registry(name, url, namespace, auth_token, priority, set_default)

        click.echo(
            click.style("✓ ", fg="green") + f"Added registry: {click.style(name, fg='cyan')}"
        )
        click.echo(f"  URL: {url}")
        if namespace:
            click.echo(f"  Namespace: {namespace}")
        if priority:
            click.echo(f"  Priority: {priority}")
        if set_default:
            click.echo(click.style("  Set as default registry", fg="yellow"))

    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Failed to add registry: {str(e)}", err=True)
        raise click.Abort()


@registry.command("list")
def registry_list() -> None:
    """List configured registries."""
    try:
        config = SutrasConfig()
        registries = config.list_registries()

        if not registries:
            click.echo(click.style("No registries configured", fg="yellow"))
            click.echo("\nAdd a registry with:")
            click.echo(click.style("  sutras registry add <name> <url>", fg="cyan", bold=True))
            return

        click.echo(
            click.style(f"Configured registries ({len(registries)}):", fg="green", bold=True)
        )
        click.echo()

        default = config.config.default_registry
        for name, reg in sorted(registries.items(), key=lambda x: x[1].priority, reverse=True):
            is_default = name == default
            prefix = click.style("★ ", fg="yellow") if is_default else "  "
            click.echo(f"{prefix}{click.style(name, fg='cyan', bold=True)}")
            click.echo(f"    URL: {reg.url}")
            if reg.namespace:
                click.echo(f"    Namespace: {reg.namespace}")
            if reg.priority:
                click.echo(f"    Priority: {reg.priority}")
            status = (
                click.style("enabled", fg="green")
                if reg.enabled
                else click.style("disabled", fg="red")
            )
            click.echo(f"    Status: {status}")
            if is_default:
                click.echo(click.style("    (default)", fg="yellow"))
            click.echo()

    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Failed to list registries: {str(e)}", err=True)
        raise click.Abort()


@registry.command("remove")
@click.argument("name")
def registry_remove(name: str) -> None:
    """Remove a registry."""
    try:
        config = SutrasConfig()
        config.remove_registry(name)

        click.echo(click.style("✓ ", fg="green") + f"Removed registry: {name}")

    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Failed to remove registry: {str(e)}", err=True)
        raise click.Abort()


@registry.command("update")
@click.argument("name", required=False)
@click.option("--all", "update_all", is_flag=True, help="Update all registries")
def registry_update(name: str | None, update_all: bool) -> None:
    """Update cached registry indexes."""
    try:
        manager = RegistryManager()

        if update_all:
            with spinner("Updating all registries", "All registries updated"):
                manager.update_all_registries()
        elif name:
            with spinner(f"Updating registry: {name}", f"Updated registry: {name}"):
                manager.update_registry(name)
        else:
            click.echo(
                click.style("✗ ", fg="red") + "Specify a registry name or use --all", err=True
            )
            raise click.Abort()

    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Failed to update registry: {str(e)}", err=True)
        raise click.Abort()


@registry.command("build-index")
@click.argument("registry_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for index.yaml (default: <registry_path>/index.yaml)",
)
def registry_build_index(registry_path: Path, output: Path | None) -> None:
    """Generate index.yaml for a local registry."""
    try:
        click.echo(click.style(f"Building index for: {registry_path}", fg="cyan"))

        manager = RegistryManager()
        manager.build_index(registry_path, output)

        output_path = output or registry_path / "index.yaml"
        click.echo(click.style("✓ ", fg="green") + f"Index built: {output_path}")

    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Failed to build index: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("source")
@click.option("--version", "-v", help="Specific version (for registry installs)")
@click.option("--registry", "-r", help="Registry to install from (for registry installs)")
@click.pass_context
def install(ctx: click.Context, source: str, version: str | None, registry: str | None) -> None:
    """Install a skill from various sources.

    SOURCE can be:

    \b
    - Registry skill: @namespace/skill-name
    - GitHub release: github:user/repo@version or github:user/repo
    - Direct URL: https://example.com/skill.tar.gz
    - Local file: ./skill.tar.gz or /path/to/skill.tar.gz

    Examples:

    \b
    sutras install @username/my-skill
    sutras install @username/my-skill --version 1.2.0
    sutras install github:user/repo@v1.0.0
    sutras install https://example.com/skills/skill-1.0.0.tar.gz
    sutras install ./dist/my-skill-1.0.0.tar.gz
    """
    verbose = _verbose(ctx)
    try:
        if verbose:
            click.echo(click.style("Install details:", fg="bright_black"))
            click.echo(click.style(f"  Source: {source}", fg="bright_black"))
            if version:
                click.echo(click.style(f"  Version: {version}", fg="bright_black"))
            if registry:
                click.echo(click.style(f"  Registry: {registry}", fg="bright_black"))
            click.echo()

        installer = SkillInstaller()
        with spinner("Installing skill", f"Installed {source}"):
            installer.install(source, version, registry)

        click.echo()
        click.echo(click.style("Next steps:", fg="yellow", bold=True))
        click.echo("  - Use the skill with Claude")
        click.echo(f"  - Run: {click.style('sutras list', fg='green')} to see installed skills")

    except ValueError as e:
        operation_failed(
            "Installation",
            str(e),
            [
                f"Run {click.style('sutras install --help', fg='cyan')} for usage examples",
                "Check the source format: @namespace/skill, github:user/repo, URL, or local path",
            ],
        )
    except Exception as e:
        operation_failed("Installation", str(e))


@cli.command()
@click.argument("skill_name")
@click.option("--version", "-v", help="Specific version to uninstall (default: all versions)")
def uninstall(skill_name: str, version: str | None) -> None:
    """Uninstall a skill."""
    try:
        installer = SkillInstaller()
        installer.uninstall(skill_name, version)

    except ValueError as e:
        operation_failed(
            "Uninstall",
            str(e),
            [
                f"Run {click.style('sutras list', fg='cyan')} to see installed skills",
            ],
        )
    except Exception as e:
        operation_failed("Uninstall", str(e))


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--registry", "-r", help="Registry to publish to (default: default registry)")
@click.option("--pr", is_flag=True, help="Use pull request workflow instead of direct push")
@click.option("--build-dir", "-b", type=click.Path(path_type=Path), help="Custom build directory")
def publish(skill_path: Path, registry: str | None, pr: bool, build_dir: Path | None) -> None:
    """Publish a skill to a registry."""
    try:
        publisher = SkillPublisher()
        with spinner("Publishing skill"):
            publisher.publish(skill_path, registry, pr, build_dir)

    except PublishError as e:
        operation_failed(
            "Publishing",
            str(e),
            [
                f"Run {click.style('sutras registry list', fg='cyan')} to check registry config",
                f"Run {click.style('sutras validate', fg='cyan')} to check skill validity",
            ],
        )
    except Exception as e:
        operation_failed("Publishing", str(e))


@cli.command()
@click.option(
    "--check",
    is_flag=True,
    help="Show what would be installed without making changes",
)
@click.option(
    "--uninstall",
    is_flag=True,
    help="Remove the sutras skill from Claude Code",
)
def setup(check: bool, uninstall: bool) -> None:
    """Install the sutras skill into Claude Code's global skills directory.

    Copies the bundled SKILL.md to ~/.claude/skills/sutras/ so Claude Code
    can discover and use sutras commands.
    """
    target_dir = Path.home() / ".claude" / "skills" / "sutras"
    target_file = target_dir / "SKILL.md"

    if uninstall:
        if target_file.exists():
            target_file.unlink()
            if target_dir.exists() and not any(target_dir.iterdir()):
                target_dir.rmdir()
            click.echo(click.style("✓ ", fg="green") + "Sutras skill removed from Claude Code")
        else:
            click.echo(click.style("⚠ ", fg="yellow") + "Sutras skill not installed")
        return

    # Locate bundled SKILL.md
    from importlib.resources import files as resource_files

    skill_resource = resource_files("sutras").joinpath("data", "skills", "sutras", "SKILL.md")
    try:
        skill_content = skill_resource.read_text(encoding="utf-8")
    except FileNotFoundError:
        click.echo(
            click.style("✗ ", fg="red") + "Bundled SKILL.md not found in package data",
            err=True,
        )
        raise click.Abort()

    if check:
        click.echo(click.style("Would install:", fg="cyan", bold=True))
        click.echo(f"  {target_file}")
        if target_file.exists():
            click.echo(click.style("  (exists, would be overwritten)", fg="yellow"))
        else:
            click.echo(click.style("  (new file)", fg="green"))
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(skill_content)

    click.echo(click.style("✓ ", fg="green", bold=True) + "Sutras skill installed for Claude Code")
    click.echo(click.style(f"  {target_file}", fg="cyan"))
    click.echo()
    click.echo(
        click.style("The skill will be available next time Claude Code starts.", fg="bright_black")
    )


@cli.command()
@click.option(
    "--version",
    "-v",
    "target_version",
    default=None,
    help="Update to a specific version (default: latest)",
)
@click.option(
    "--check",
    is_flag=True,
    help="Only check if an update is available, don't install",
)
@click.option(
    "--skip-pi",
    is_flag=True,
    help="Skip updating the pi extension",
)
@click.option(
    "--skip-skill",
    is_flag=True,
    help="Skip refreshing the global skill (~/.claude/skills/sutras/)",
)
def update(target_version: str | None, check: bool, skip_pi: bool, skip_skill: bool) -> None:
    """Check for updates and upgrade sutras to the latest version.

    Updates all components:
    - Python CLI (via pipx/uv/pip)
    - pi extension (via pi/pnpm/npm)
    - Global skill (~/.claude/skills/sutras/SKILL.md)

    \b
    Examples:
      sutras update                # Update everything to latest
      sutras update --check        # Just check, don't install
      sutras update -v 0.5.0       # Pin to a specific version
      sutras update --skip-pi      # Update CLI + skill only
    """
    from sutras.core.updater import (
        check_update_available,
        update_all,
    )

    current, latest = check_update_available()

    if check:
        click.echo(click.style(f"Current version: {current}", fg="cyan"))
        if latest:
            click.echo(click.style(f"Latest version:  {latest}", fg="green", bold=True))
            click.echo()
            click.echo(f"Run {click.style('sutras update', fg='cyan')} to upgrade.")
        else:
            click.echo(click.style("✓ Already up-to-date!", fg="green"))
        return

    if not target_version and not latest:
        click.echo(click.style(f"✓ sutras {current} is already the latest version.", fg="green"))
        # Still refresh skill in case it's stale
        if not skip_skill:
            from sutras.core.updater import refresh_global_skill

            result = refresh_global_skill()
            if result.updated:
                click.echo(click.style("✓ ", fg="green") + "Refreshed global skill")
        return

    effective_version = target_version or latest
    click.echo(
        click.style(f"Updating sutras {current} → {effective_version}", fg="cyan", bold=True)
    )
    click.echo()

    summary = update_all(
        target_version=target_version,
        skip_pi=skip_pi,
        skip_skill=skip_skill,
    )

    LABELS = {
        "cli": "Python CLI",
        "pi-extension": "pi extension",
        "global-skill": "Global skill",
    }

    for result in summary.results:
        label = LABELS.get(result.component, result.component)

        if result.updated:
            version_info = ""
            if result.old_version and result.new_version:
                version_info = f" ({result.old_version} → {result.new_version})"
            elif result.new_version:
                version_info = f" ({result.new_version})"
            click.echo(click.style("✓ ", fg="green") + f"{label} updated{version_info}")

        elif result.skipped:
            if result.error:
                msg = f"{label} skipped — {result.error}"
                click.echo(click.style("⊘ ", fg="bright_black") + msg)
            else:
                click.echo(click.style("· ", fg="bright_black") + f"{label} already up-to-date")

        elif result.error:
            click.echo(click.style("✗ ", fg="red") + f"{label} failed: {result.error}")

    click.echo()

    if summary.any_updated:
        click.echo(click.style("✓ Update complete!", fg="green", bold=True))
        click.echo(
            click.style(
                "  Restart your terminal or pi session to use the new version.",
                fg="bright_black",
            )
        )
    elif not summary.any_errors:
        click.echo(click.style("✓ Everything is up-to-date.", fg="green"))
    else:
        click.echo(click.style("⚠ Some components could not be updated.", fg="yellow"))
        click.echo("  See errors above for details.")


@cli.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """Generate shell completion script.

    Output a completion script for the given shell. Source it in your
    shell profile to enable tab-completion for all sutras commands.

    \b
    Examples:
      sutras completion bash >> ~/.bashrc
      sutras completion zsh >> ~/.zshrc
      sutras completion fish > ~/.config/fish/completions/sutras.fish
    """
    env_var = "_SUTRAS_COMPLETE"
    shells = {
        "bash": f"{env_var}=bash_source sutras",
        "zsh": f"{env_var}=zsh_source sutras",
        "fish": f"{env_var}=fish_source sutras",
    }

    import os
    import subprocess

    env = os.environ.copy()
    env[env_var] = f"{shell}_source"
    try:
        result = subprocess.run(
            ["sutras"],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            click.echo(result.stdout)
        else:
            click.echo(result.stderr)
    except FileNotFoundError:
        # Fallback: emit manual instructions
        click.echo(f"# Run the following to enable {shell} completion:")
        click.echo(f'#   eval "$({shells[shell]})"')
        click.echo(f'eval "$({shells[shell]})"')


if __name__ == "__main__":
    cli()

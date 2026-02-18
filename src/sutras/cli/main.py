"""Main CLI entry point for sutras - skill devtool."""

from datetime import datetime
from pathlib import Path

import click

from sutras import SkillLoader, __version__
from sutras.core.builder import BuildError, SkillBuilder
from sutras.core.config import SutrasConfig
from sutras.core.docgen import generate_docs, write_docs
from sutras.core.evaluator import Evaluator
from sutras.core.installer import SkillInstaller
from sutras.core.publisher import PublishError, SkillPublisher
from sutras.core.registry import RegistryManager
from sutras.core.test_runner import TestRunner


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """
    Sutras - Devtool for Anthropic Agent Skills.

    Create, evaluate, test, distribute, and discover skills with ease.
    """
    pass


@cli.command()
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
def list(local: bool, global_: bool) -> None:
    """List available skills."""
    try:
        loader = SkillLoader(include_project=local, include_global=global_)
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

    except FileNotFoundError as e:
        click.echo(click.style(f"✗ Skill not found: {name}", fg="red"), err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except ValueError as e:
        click.echo(click.style(f"✗ Invalid skill format: {name}", fg="red"), err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"✗ Error loading skill: {str(e)}", fg="red"), err=True)
        raise click.Abort()


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
def test(name: str, verbose: bool, fail_fast: bool) -> None:
    """Run tests for a skill."""
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
        click.echo(click.style("✗ ", fg="red") + f"Skill not found: {name}", err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Error running tests: {str(e)}", err=True)
        raise click.Abort()


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
def eval(name: str, verbose: bool, no_history: bool, show_history: bool) -> None:
    """Evaluate a skill using configured metrics."""
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
        click.echo(click.style("✗ ", fg="red") + f"Skill not found: {name}", err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + f"Configuration error: {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Error running evaluation: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("name")
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict validation (warnings become errors)",
)
def validate(name: str, strict: bool) -> None:
    """Validate a skill's structure and metadata."""
    loader = SkillLoader()
    warnings = []
    errors = []

    try:
        click.echo(click.style(f"Validating skill: {name}", fg="cyan", bold=True))
        click.echo()

        skill = loader.load(name)

        click.echo(click.style("✓", fg="green") + " SKILL.md found and parsed")

        if not skill.name:
            errors.append("Missing skill name")
        else:
            click.echo(
                click.style("✓", fg="green") + f" Valid name: {click.style(skill.name, fg='cyan')}"
            )

        if not skill.description:
            errors.append("Missing skill description")
        else:
            desc_len = len(skill.description)
            if desc_len < 50:
                warnings.append(
                    f"Description is short ({desc_len} chars, recommend 50+ for Claude discovery)"
                )
            click.echo(click.style("✓", fg="green") + f" Valid description ({desc_len} chars)")

        if skill.abi:
            click.echo(click.style("✓", fg="green") + " sutras.yaml found and parsed")

            if not skill.abi.version:
                warnings.append("Missing version in sutras.yaml")
            else:
                click.echo(
                    click.style("✓", fg="green")
                    + f" Version: {click.style(skill.abi.version, fg='blue')}"
                )

            if not skill.abi.author:
                warnings.append("Missing author in sutras.yaml")
            else:
                click.echo(click.style("✓", fg="green") + f" Author: {skill.abi.author}")

            if not skill.abi.license:
                warnings.append("Missing license in sutras.yaml (recommended for distribution)")

            if skill.abi.distribution:
                if not skill.abi.distribution.tags:
                    warnings.append("No tags specified (helps with skill discovery)")
                if not skill.abi.distribution.category:
                    warnings.append("No category specified (helps with skill organization)")
        else:
            warnings.append("No sutras.yaml found (recommended for lifecycle management)")

        if skill.allowed_tools:
            click.echo(
                click.style("✓", fg="green") + f" Allowed tools: {', '.join(skill.allowed_tools)}"
            )

        if skill.supporting_files:
            click.echo(
                click.style("✓", fg="green")
                + f" {len(skill.supporting_files)} supporting file(s) found"
            )

        click.echo()

        if warnings:
            click.echo(click.style(f"Warnings ({len(warnings)}):", fg="yellow", bold=True))
            for warning in warnings:
                click.echo(click.style("  ⚠ ", fg="yellow") + warning)
            click.echo()

        if errors:
            click.echo(click.style(f"Errors ({len(errors)}):", fg="red", bold=True))
            for error in errors:
                click.echo(click.style("  ✗ ", fg="red") + error)
            click.echo()
            raise click.Abort()

        if strict and warnings:
            click.echo(
                click.style(
                    "✗ Validation failed (strict mode: warnings treated as errors)",
                    fg="red",
                    bold=True,
                )
            )
            raise click.Abort()

        click.echo(
            click.style("✓ ", fg="green", bold=True)
            + click.style(f"Skill '{skill.name}' is valid!", fg="green")
        )

    except FileNotFoundError as e:
        click.echo(click.style("✗ ", fg="red") + f"Skill not found: {name}", err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + f"Invalid skill format: {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        if "Validation failed" not in str(e):
            click.echo(
                click.style("✗ ", fg="red") + f"Error validating skill: {str(e)}",
                err=True,
            )
        raise click.Abort()


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
        click.echo(click.style("✗ ", fg="red") + f"Skill not found: {name}", err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except Exception as e:
        click.echo(
            click.style("✗ ", fg="red") + f"Error generating docs: {str(e)}",
            err=True,
        )
        raise click.Abort()


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
def build(name: str, output: Path | None, no_validate: bool) -> None:
    """Build a distributable package for a skill."""
    loader = SkillLoader()

    try:
        click.echo(click.style(f"Building skill: {name}", fg="cyan", bold=True))
        click.echo()

        skill = loader.load(name)

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

        click.echo(click.style("Packaging skill...", fg="blue"))

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
        click.echo(click.style("✗ ", fg="red") + f"Skill not found: {name}", err=True)
        click.echo(click.style(f"  {str(e)}", fg="yellow"), err=True)
        click.echo("\nRun 'sutras list' to see available skills")
        raise click.Abort()
    except BuildError as e:
        click.echo(click.style("✗ Build failed: ", fg="red") + str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Error building skill: {str(e)}", err=True)
        raise click.Abort()


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
            click.echo(click.style("Updating all registries...", fg="cyan"))
            manager.update_all_registries()
            click.echo(click.style("✓ ", fg="green") + "All registries updated")
        elif name:
            click.echo(click.style(f"Updating registry: {name}", fg="cyan"))
            manager.update_registry(name)
            click.echo(click.style("✓ ", fg="green") + f"Updated registry: {name}")
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
def install(source: str, version: str | None, registry: str | None) -> None:
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
    try:
        installer = SkillInstaller()
        installer.install(source, version, registry)

        click.echo()
        click.echo(click.style("Next steps:", fg="yellow", bold=True))
        click.echo("  - Use the skill with Claude")
        click.echo(f"  - Run: {click.style('sutras list', fg='green')} to see installed skills")

    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Installation failed: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("skill_name")
@click.option("--version", "-v", help="Specific version to uninstall (default: all versions)")
def uninstall(skill_name: str, version: str | None) -> None:
    """Uninstall a skill."""
    try:
        installer = SkillInstaller()
        installer.uninstall(skill_name, version)

    except ValueError as e:
        click.echo(click.style("✗ ", fg="red") + str(e), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Uninstallation failed: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--registry", "-r", help="Registry to publish to (default: default registry)")
@click.option("--pr", is_flag=True, help="Use pull request workflow instead of direct push")
@click.option("--build-dir", "-b", type=click.Path(path_type=Path), help="Custom build directory")
def publish(skill_path: Path, registry: str | None, pr: bool, build_dir: Path | None) -> None:
    """Publish a skill to a registry."""
    try:
        publisher = SkillPublisher()
        publisher.publish(skill_path, registry, pr, build_dir)

    except PublishError as e:
        click.echo(click.style("✗ ", fg="red") + f"Publishing failed: {str(e)}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style("✗ ", fg="red") + f"Error during publishing: {str(e)}", err=True)
        raise click.Abort()


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


if __name__ == "__main__":
    cli()

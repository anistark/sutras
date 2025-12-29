"""Main CLI entry point for sutras - skill devtool."""

from pathlib import Path

import click

from sutras import SkillLoader, __version__
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
                version_str = f" {click.style(f'v{skill.version}', fg='blue')}" if skill.version else ""
                click.echo(f"  {click.style(skill.name, fg='cyan', bold=True)}{version_str}")

                desc = skill.description
                if len(desc) > 100:
                    desc = desc[:97] + "..."
                click.echo(f"    {desc}")

                if skill.path:
                    click.echo(click.style(f"    {skill.path}", fg="bright_black"))
                click.echo()
            except Exception as e:
                click.echo(f"  {click.style(skill_name, fg='red')} {click.style('(failed to load)', fg='yellow')}")
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
@click.argument("name")
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
    "--global",
    "global_",
    is_flag=True,
    help="Create in global skills directory (~/.claude/skills/)",
)
def new(name: str, description: str | None, author: str | None, global_: bool) -> None:
    """Create a new skill with proper structure."""
    if not name.replace("-", "").replace("_", "").isalnum():
        click.echo(
            click.style("✗ ", fg="red") + "Skill name must contain only alphanumeric characters, hyphens, and underscores",
            err=True,
        )
        raise click.Abort()

    name = name.lower()

    if global_:
        skills_dir = Path.home() / ".claude" / "skills"
    else:
        skills_dir = Path.cwd() / ".claude" / "skills"

    skill_dir = skills_dir / name

    if skill_dir.exists():
        click.echo(click.style("✗ ", fg="red") + f"Skill '{name}' already exists at {skill_dir}", err=True)
        raise click.Abort()

    click.echo(click.style(f"Creating skill: {name}", fg="cyan", bold=True))
    click.echo()

    # Create directory structure
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create SKILL.md
    description = description or f"Description of {name} skill"
    skill_md_content = f"""---
name: {name}
description: {description}
---

# {name.replace("-", " ").title()}

## Instructions

Add your skill instructions here. Provide step-by-step guidance for Claude
on how to use this skill effectively.

1. First step
2. Second step
3. Third step

## When to Use

Describe the scenarios when Claude should invoke this skill.

## Examples

Provide concrete examples of how this skill works.
"""

    (skill_dir / "SKILL.md").write_text(skill_md_content)

    # Create sutras.yaml
    author = author or "Skill Author"
    sutras_yaml_content = f"""version: "0.1.0"
author: "{author}"
license: "MIT"

# Capability declarations
capabilities:
  tools: []
  dependencies: []
  constraints: {{}}

# Test configuration (optional)
# tests:
#   cases:
#     - name: "basic-test"
#       inputs:
#         example: "value"
#       expected:
#         result: "expected"

# Evaluation configuration (optional)
# eval:
#   framework: "ragas"
#   metrics: ["correctness"]

# Distribution metadata
distribution:
  tags: []
  category: "general"
"""

    (skill_dir / "sutras.yaml").write_text(sutras_yaml_content)

    # Create examples.md
    examples_md_content = f"""# {name.replace("-", " ").title()} - Examples

## Example 1: Basic Usage

Description of basic usage scenario.

## Example 2: Advanced Usage

Description of advanced usage scenario.
"""

    (skill_dir / "examples.md").write_text(examples_md_content)

    click.echo(click.style("✓ ", fg="green") + "Created SKILL.md")
    click.echo(click.style("✓ ", fg="green") + "Created sutras.yaml")
    click.echo(click.style("✓ ", fg="green") + "Created examples.md")
    click.echo()
    click.echo(click.style("✓ Success!", fg="green", bold=True) + f" Skill created at:")
    click.echo(click.style(f"  {skill_dir}", fg="cyan"))
    click.echo()
    click.echo(click.style("Next steps:", fg="yellow", bold=True))
    click.echo(f"  1. Edit {click.style('SKILL.md', fg='cyan')} to define your skill")
    click.echo(f"  2. Update {click.style('sutras.yaml', fg='cyan')} with metadata")
    click.echo(f"  3. Run: {click.style(f'sutras info {name}', fg='green')}")
    click.echo(f"  4. Validate: {click.style(f'sutras validate {name}', fg='green')}")
    click.echo(f"  5. Test your skill with Claude")


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
            click.echo(click.style("""
tests:
  cases:
    - name: "basic-test"
      inputs:
        example: "value"
      expected:
        status: "success"
""", fg="bright_black"))
            return

        runner = TestRunner(skill)

        if verbose:
            click.echo(click.style(f"Test configuration:", fg="blue"))
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
                click.style("✓ ", fg="green", bold=True) +
                click.style(f"{summary.passed}/{summary.total} tests passed", fg="green")
            )
        else:
            click.echo(
                click.style("✗ ", fg="red", bold=True) +
                click.style(
                    f"{summary.failed}/{summary.total} tests failed",
                    fg="red"
                )
            )

        if skill.abi.tests.coverage_threshold and summary.total > 0:
            pass_rate = (summary.passed / summary.total) * 100
            threshold = skill.abi.tests.coverage_threshold
            if pass_rate >= threshold:
                click.echo(
                    click.style(
                        f"✓ Coverage threshold met: {pass_rate:.1f}% >= {threshold}%",
                        fg="green"
                    )
                )
            else:
                click.echo(
                    click.style(
                        f"✗ Coverage threshold not met: {pass_rate:.1f}% < {threshold}%",
                        fg="red"
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
            click.echo(click.style("✓", fg="green") + f" Valid name: {click.style(skill.name, fg='cyan')}")

        if not skill.description:
            errors.append("Missing skill description")
        else:
            desc_len = len(skill.description)
            if desc_len < 50:
                warnings.append(f"Description is short ({desc_len} chars, recommend 50+ for Claude discovery)")
            click.echo(click.style("✓", fg="green") + f" Valid description ({desc_len} chars)")

        if skill.abi:
            click.echo(click.style("✓", fg="green") + " sutras.yaml found and parsed")

            if not skill.abi.version:
                warnings.append("Missing version in sutras.yaml")
            else:
                click.echo(click.style("✓", fg="green") + f" Version: {click.style(skill.abi.version, fg='blue')}")

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
            click.echo(click.style("✓", fg="green") + f" Allowed tools: {', '.join(skill.allowed_tools)}")

        if skill.supporting_files:
            click.echo(click.style("✓", fg="green") + f" {len(skill.supporting_files)} supporting file(s) found")

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
            click.echo(click.style("✗ Validation failed (strict mode: warnings treated as errors)", fg="red", bold=True))
            raise click.Abort()

        click.echo(click.style("✓ ", fg="green", bold=True) + click.style(f"Skill '{skill.name}' is valid!", fg="green"))

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
            click.echo(click.style("✗ ", fg="red") + f"Error validating skill: {str(e)}", fg="red", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()

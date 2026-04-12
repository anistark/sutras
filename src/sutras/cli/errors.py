"""Centralized error handling for the Sutras CLI.

Provides consistent, user-friendly error messages with actionable suggestions.
"""

from __future__ import annotations

import click


def skill_not_found(name: str, detail: str | None = None) -> None:
    """Report a skill-not-found error with actionable guidance."""
    click.echo(click.style(f"Error: Skill '{name}' not found.", fg="red", bold=True), err=True)
    if detail:
        click.echo(click.style(f"  {detail}", fg="yellow"), err=True)
    click.echo(err=True)
    click.echo("Suggestions:", err=True)
    click.echo(f"  - Run {click.style('sutras list', fg='cyan')} to see available skills", err=True)
    click.echo(f"  - Run {click.style(f'sutras new {name}', fg='cyan')} to create it", err=True)
    raise click.Abort()


def invalid_skill(name: str, detail: str) -> None:
    """Report an invalid/malformed skill with fix guidance."""
    click.echo(
        click.style(f"Error: Skill '{name}' has invalid format.", fg="red", bold=True),
        err=True,
    )
    click.echo(click.style(f"  {detail}", fg="yellow"), err=True)
    click.echo(err=True)
    click.echo("Suggestions:", err=True)
    validate_cmd = click.style(f"sutras validate {name}", fg="cyan")
    click.echo(f"  - Run {validate_cmd} for detailed diagnostics", err=True)
    click.echo(
        "  - Ensure SKILL.md has valid YAML frontmatter with 'name' and 'description'",
        err=True,
    )
    raise click.Abort()


def missing_config(what: str, fix: str) -> None:
    """Report missing configuration with a fix command."""
    click.echo(click.style(f"Error: {what}", fg="red", bold=True), err=True)
    click.echo(err=True)
    click.echo(f"  Fix: {click.style(fix, fg='cyan')}", err=True)
    raise click.Abort()


def operation_failed(operation: str, detail: str, suggestions: list[str] | None = None) -> None:
    """Report a failed operation with optional suggestions."""
    click.echo(
        click.style(f"Error: {operation} failed.", fg="red", bold=True),
        err=True,
    )
    click.echo(click.style(f"  {detail}", fg="yellow"), err=True)
    if suggestions:
        click.echo(err=True)
        click.echo("Suggestions:", err=True)
        for s in suggestions:
            click.echo(f"  - {s}", err=True)
    raise click.Abort()

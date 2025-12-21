"""Main CLI entry point for sutras - skill devtool."""

from pathlib import Path

import click

from sutras import SkillLoader, __version__


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
    loader = SkillLoader(include_project=local, include_global=global_)
    skills = loader.discover()

    if not skills:
        click.echo("No skills found.")
        click.echo("\nCreate a new skill with: sutras new <skill-name>")
        return

    click.echo(f"Found {len(skills)} skill(s):\n")

    for skill_name in skills:
        try:
            skill = loader.load(skill_name)
            version_str = f" (v{skill.version})" if skill.version else ""
            click.echo(f"  {skill.name}{version_str}")
            click.echo(f"    {skill.description[:80]}...")
        except Exception:
            click.echo(f"  {skill_name} (failed to load)")


@cli.command()
@click.argument("name")
def info(name: str) -> None:
    """Show detailed information about a skill."""
    loader = SkillLoader()

    try:
        skill = loader.load(name)

        click.echo(f"Skill: {skill.name}")
        click.echo(f"Path: {skill.path}")
        click.echo("\nDescription:")
        click.echo(f"  {skill.description}")

        if skill.version:
            click.echo(f"\nVersion: {skill.version}")

        if skill.author:
            click.echo(f"Author: {skill.author}")

        if skill.allowed_tools:
            click.echo(f"\nAllowed Tools: {', '.join(skill.allowed_tools)}")

        if skill.abi:
            if skill.abi.license:
                click.echo(f"License: {skill.abi.license}")

            if skill.abi.repository:
                click.echo(f"Repository: {skill.abi.repository}")

            if skill.abi.distribution and skill.abi.distribution.tags:
                tags = ", ".join(skill.abi.distribution.tags)
                click.echo(f"Tags: {tags}")

        if skill.supporting_files:
            click.echo("\nSupporting Files:")
            for filename in sorted(skill.supporting_files.keys()):
                click.echo(f"  - {filename}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"Error: Invalid skill format - {e}", err=True)
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
    # Validate skill name
    if not name.replace("-", "").replace("_", "").isalnum():
        click.echo(
            "Error: Skill name must contain only alphanumeric characters, hyphens, and underscores",
            err=True,
        )
        raise click.Abort()

    name = name.lower()

    # Determine target directory
    if global_:
        skills_dir = Path.home() / ".claude" / "skills"
    else:
        skills_dir = Path.cwd() / ".claude" / "skills"

    skill_dir = skills_dir / name

    if skill_dir.exists():
        click.echo(f"Error: Skill '{name}' already exists at {skill_dir}", err=True)
        raise click.Abort()

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

    click.echo(f"Created new skill at {skill_dir}")
    click.echo("\nNext steps:")
    click.echo(f"  1. Edit {skill_dir / 'SKILL.md'} to define your skill")
    click.echo(f"  2. Update {skill_dir / 'sutras.yaml'} with metadata")
    click.echo(f"  3. Run: sutras info {name}")
    click.echo("  4. Test your skill with Claude")


@cli.command()
@click.argument("name")
def validate(name: str) -> None:
    """Validate a skill's structure and metadata."""
    loader = SkillLoader()

    try:
        skill = loader.load(name)

        click.echo(f"Validating skill: {skill.name}")

        # Check SKILL.md
        click.echo("✓ SKILL.md found and parsed")

        # Validate metadata
        if not skill.name:
            click.echo("✗ Missing skill name", err=True)
            raise click.Abort()
        click.echo(f"✓ Valid name: {skill.name}")

        if not skill.description:
            click.echo("✗ Missing skill description", err=True)
            raise click.Abort()

        if len(skill.description) < 50:
            click.echo(
                "⚠ Description is too short (should be detailed for Claude discovery)", err=True
            )

        click.echo(f"✓ Valid description ({len(skill.description)} chars)")

        # Check sutras.yaml if present
        if skill.abi:
            click.echo("✓ sutras.yaml found and parsed")

            if not skill.abi.version:
                click.echo("⚠ Missing version in sutras.yaml")
        else:
            click.echo("⚠ No sutras.yaml found (recommended for lifecycle management)")

        click.echo(f"\n✓ Skill '{skill.name}' is valid!")

    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"✗ Invalid skill format: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()

---
name: sutras
description: >
  Create, validate, test, build, and distribute Anthropic Agent Skills using the Sutras CLI.
  Use when the user asks to create a new skill, scaffold skill structure, validate SKILL.md files,
  manage skill metadata, run skill tests/evaluations, build distributable packages, or publish
  skills to registries. Requires sutras >= 0.4.1.
---

# Sutras — Skill Development Toolkit

Sutras is a CLI for the full lifecycle of Anthropic Agent Skills:
scaffolding, validation, testing, evaluation, packaging, and distribution.

## Prerequisites

Before running any sutras command, verify the CLI is installed:

```bash
sutras --version
```

If the command is not found, **ask the user** to install it before proceeding.
Suggest the install method based on what is available on their system:

| Tool available | Install command |
|---------------|-----------------|
| `pipx` | `pipx install sutras` |
| `uv` | `uv tool install sutras` |
| `pip` / `pip3` | `pip install --user sutras` |

Check in this order: `pipx`, `uv`, `pip3`, `pip`. Use the first one found.
Do NOT run the install command without the user's confirmation.

## Command Reference

```
sutras build <name>
    Build a distributable package for a skill.
    --output/-o: Output directory for the package (default: ./dist)
    --no-validate (flag): Skip validation before building

sutras docs <name>
    Generate documentation for a skill.
    --output/-o: Output file or directory (default: print to stdout)
    --no-supporting (flag): Exclude supporting file contents (examples.md, etc.)

sutras eval <name>
    Evaluate a skill using configured metrics.
    --verbose/-v (flag): Enable verbose evaluation output
    --no-history (flag): Don't save evaluation results to history
    --show-history (flag): Show evaluation history for this skill

sutras info <name>
    Show detailed information about a skill.

sutras install <source>
    Install a skill from various sources.
    --version/-v: Specific version (for registry installs)
    --registry/-r: Registry to install from (for registry installs)

sutras list
    List available skills.
    --local (flag): Include project skills from .claude/skills/
    --global (flag): Include global skills from ~/.claude/skills/

sutras new [name]
    Create a new skill with proper structure.
    --description/-d: Skill description (what it does and when to use it)
    --author/-a: Skill author name
    --template/-t: Template to use (run with --list-templates to see options)
    --list-templates (flag): List available skill templates
    --global (flag): Create in global skills directory (~/.claude/skills/)

sutras publish [skill_path]
    Publish a skill to a registry.
    --registry/-r: Registry to publish to (default: default registry)
    --pr (flag): Use pull request workflow instead of direct push
    --build-dir/-b: Custom build directory

sutras registry add <name> <url>
    Add a new registry.
    --namespace/-n: Default namespace for this registry
    --auth-token/-t: Authentication token
    --priority/-p: Registry priority (higher = checked first)
    --default (flag): Set as default registry

sutras registry build-index <registry_path>
    Generate index.yaml for a local registry.
    --output/-o: Output path for index.yaml (default: <registry_path>/index.yaml)

sutras registry list
    List configured registries.

sutras registry remove <name>
    Remove a registry.

sutras registry update [name]
    Update cached registry indexes.
    --all (flag): Update all registries

sutras setup
    Install the sutras skill into Claude Code's global skills directory.
    --check (flag): Show what would be installed without making changes
    --uninstall (flag): Remove the sutras skill from Claude Code

sutras test <name>
    Run tests for a skill.
    --verbose/-v (flag): Enable verbose test output
    --fail-fast/-x (flag): Stop on first test failure

sutras uninstall <skill_name>
    Uninstall a skill.
    --version/-v: Specific version to uninstall (default: all versions)

sutras validate <name>
    Validate a skill's structure and metadata.
    --strict (flag): Enable strict validation (warnings become errors)
```

## SKILL.md Format

Every skill requires a `SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: >
  What it does and when the agent should use it.
  Be specific — the description drives skill discovery.
allowed-tools: Read, Write, Bash
---
```

Name rules: lowercase a-z, 0-9, hyphens only, max 64 chars.

## sutras.yaml Format

Extended metadata for lifecycle management:

```yaml
version: "1.0.0"
author: "Your Name"
license: "MIT"

capabilities:
  tools: [Read, Write, Bash]
  dependencies:
    - name: "@utils/common"
      version: "^1.0.0"

tests:
  cases:
    - name: "basic-test"
      inputs: {example: "value"}
      expected: {status: "success"}

eval:
  framework: "ragas"
  metrics: ["faithfulness", "answer_relevancy"]
  threshold: 0.7

distribution:
  tags: ["automation", "pdf"]
  category: "document-processing"
```

## Skill Locations

| Location | Scope | Command |
|----------|-------|---------|
| `.claude/skills/` | Project (shared via git) | `sutras new <name>` |
| `~/.claude/skills/` | Global (personal) | `sutras new <name> --global` |

For pi users, add to `.pi/settings.json`:
```json
{"skills": [".claude/skills", "~/.claude/skills"]}
```

## Best Practices

1. Write clear, specific descriptions — they drive agent skill discovery.
2. Add tests early in `sutras.yaml` to validate skill behavior.
3. Version your skills with semver for reproducible distribution.
4. Use templates (`--template code-review`, etc.) for best-practice structure.
5. Validate before sharing: `sutras validate --strict`.
6. Use scoped names for publishing: `@namespace/skill-name`.

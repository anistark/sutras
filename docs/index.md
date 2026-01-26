# Sutras

**Devtool for Anthropic Agent Skills with lifecycle management.**

![Sutras Architecture](./static/sutras-architecture.png)

Sutras is a CLI tool and library for creating, validating, and managing [Anthropic Agent Skills](https://platform.claude.com/docs/en/agent-sdk/skills). It provides scaffolding, validation, and a standardized Skill ABI for better skill organization and quality.

## Key Features

- **Scaffold**: Generate skills with proper structure and best-practice templates
- **Validate**: Check skill format, metadata, and quality standards
- **Discover**: List and inspect available skills in your workspace
- **Manage**: Organize skills with versioning and metadata
- **Test & Evaluate**: Run tests and evaluate skills with metrics
- **Package**: Build distributable tarballs with checksums
- **Distribute**: Publish and install skills from federated Git-based registries

## Why Sutras?

Creating Anthropic Skills manually requires:
- Writing SKILL.md files with correct YAML frontmatter
- Managing metadata and descriptions
- Ensuring consistent structure
- Validating format and quality

Sutras automates this with simple CLI commands.

## Installation

```sh
pip install sutras
```

Or with uv:

```sh
uv pip install sutras
```

## Quick Start

### Create a New Skill

```sh
sutras new my-skill --description "What this skill does and when to use it"
```

This creates:

```sh
.claude/skills/my-skill/
├── SKILL.md           # Skill definition with YAML frontmatter
├── sutras.yaml        # Metadata (version, author, tests, etc.)
└── examples.md        # Usage examples
```

### List Skills

```sh
sutras list
```

### View Skill Details

```sh
sutras info my-skill
```

### Validate a Skill

```sh
sutras validate my-skill

# Strict mode (warnings become errors)
sutras validate my-skill --strict
```

## Skill Structure

Every skill contains:

### SKILL.md (required)

Standard Anthropic Skills format with YAML frontmatter:

```yaml
---
name: my-skill
description: What it does and when Claude should use it
allowed-tools: Read, Write  # Optional
---

# My Skill

Instructions for Claude on how to use this skill...
```

### sutras.yaml (recommended)

Extended metadata for lifecycle management:

```yaml
version: "1.0.0"
author: "Your Name"
license: "MIT"

capabilities:
  tools: [Read, Write]
  dependencies:
    - name: "@utils/common"
      version: "^1.0.0"
    - "@tools/formatter"  # shorthand, any version

distribution:
  tags: ["automation", "pdf"]
  category: "document-processing"
```

### Dependency Version Constraints

Sutras supports npm-style semver constraints:
- **Exact**: `1.0.0` - Only version 1.0.0
- **Caret**: `^1.0.0` - Compatible with 1.x.x (>=1.0.0 <2.0.0)
- **Tilde**: `~1.2.3` - Compatible with 1.2.x (>=1.2.3 <1.3.0)
- **Ranges**: `>=1.0.0 <2.0.0` - Explicit version ranges
- **Wildcards**: `1.x`, `1.2.x`, `*` - Any matching version

### Lock Files

When dependencies are resolved, Sutras creates a `.sutras.lock` file that pins exact versions for reproducible installations. This file should be committed to version control.

### Supporting Files (optional)

- `examples.md` - Usage examples
- Additional resources as needed

## Skill Locations

Skills are stored in:
- **Project**: `.claude/skills/` (shared via git)
- **Global**: `~/.claude/skills/` (personal only)

Use `--global` flag with `sutras new` to create global skills.

## Library Usage

```python
from sutras import SkillLoader

loader = SkillLoader()
skills = loader.discover()           # Find all skills
skill = loader.load("my-skill")      # Load specific skill

print(skill.name)
print(skill.description)
print(skill.version)
```

## Examples

See [examples/skills/](https://github.com/anistark/sutras/tree/main/examples/skills/) for sample skills demonstrating best practices.

```{toctree}
:maxdepth: 2
:caption: Contents

cli
contributing
```

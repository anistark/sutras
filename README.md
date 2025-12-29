# Sutras

**Devtool for Anthropic Agent Skills with lifecycle management.**

![Sutras Architecture](./docs/static/sutras-architecture.png)

Sutras is a CLI tool and library for creating, validating, and managing [Anthropic Agent Skills](https://platform.claude.com/docs/en/agent-sdk/skills). It provides scaffolding, validation, and a standardized Skill ABI for better skill organization and quality.

[![PyPI - Version](https://img.shields.io/pypi/v/sutras)](https://pypi.org/project/sutras/)
[![PyPI Downloads](https://static.pepy.tech/badge/sutras/month)](https://pypi.org/project/sutras/)
![PyPI - Status](https://img.shields.io/pypi/status/sutras)
[![Open Source](https://img.shields.io/badge/open-source-brightgreen)](https://github.com/anistark/sutras)
![maintenance-status](https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Scaffold**: Generate skills with proper structure and best-practice templates
- **Validate**: Check skill format, metadata, and quality standards
- **Discover**: List and inspect available skills in your workspace
- **Manage**: Organize skills with versioning and metadata

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

## CLI Reference

```sh
# Create a new skill
sutras new <name> [--description TEXT] [--author TEXT] [--global]

# List skills
sutras list [--local/--no-local] [--global/--no-global]

# Show skill details
sutras info <name>

# Validate skill
sutras validate <name> [--strict]
```

### Coming Soon
- `sutras test` - Run skill tests
- `sutras eval` - Evaluate with metrics
- `sutras build` - Package for distribution
- `sutras publish` - Share to registry

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

distribution:
  tags: ["automation", "pdf"]
  category: "document-processing"
```

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

See [examples/skills/](./examples/skills/) for sample skills demonstrating best practices.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- PR process

## License

MIT License - see [LICENSE](./LICENSE)

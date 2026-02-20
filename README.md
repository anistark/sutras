# Sutras

**Devtool for Anthropic Agent Skills with lifecycle management.**

![Sutras Architecture](https://raw.githubusercontent.com/anistark/sutras/main/docs/static/sutras-architecture.png)

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
- **Test & Evaluate**: Run tests and evaluate skills with metrics
- **Package**: Build distributable tarballs with checksums
- **Distribute**: Publish and install skills from federated Git-based registries
- **Integrations**: First-class support for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [pi](https://github.com/badlogic/pi)

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

### Claude Code Integration

Install the sutras skill so Claude Code can create and manage skills:

```sh
sutras setup
```

### Pi Integration

[![npm](https://img.shields.io/npm/v/sutras)](https://www.npmjs.com/package/sutras)
[![npm downloads](https://img.shields.io/npm/dm/sutras)](https://www.npmjs.com/package/sutras)

Install the sutras extension for pi (provides `/sutras` commands):

```sh
pi install npm:sutras
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

### Skill Development

```sh
# Create a new skill
sutras new <name> [--description TEXT] [--author TEXT] [--global]

# List skills
sutras list [--local/--no-local] [--global/--no-global]

# Show skill details
sutras info <name>

# Validate skill
sutras validate <name> [--strict]

# Run tests
sutras test <name> [--verbose] [--fail-fast]

# Evaluate with metrics
sutras eval <name> [--verbose] [--no-history] [--show-history]
```

### Setup & Integrations

```sh
# Install sutras skill into Claude Code
sutras setup

# Check what would be installed
sutras setup --check

# Remove the skill from Claude Code
sutras setup --uninstall
```

### Distribution

```sh
# Build distributable package
sutras build <name> [--output PATH] [--no-validate]

# Publish to registry
sutras publish [PATH] [--registry NAME] [--pr]

# Install from various sources
sutras install <SOURCE> [--version VERSION] [--registry NAME]
# SOURCE can be:
#   @namespace/skill-name           - From registry
#   github:user/repo@version        - From GitHub release
#   https://example.com/skill.tar.gz - From URL
#   ./skill.tar.gz                  - From local file

# Uninstall skill
sutras uninstall <skill-name> [--version VERSION]
```

### Registry Management

```sh
# Add a registry
sutras registry add <name> <git-url> [--namespace NS] [--priority N] [--default]

# List registries
sutras registry list

# Remove registry
sutras registry remove <name>

# Update registry index
sutras registry update <name>
sutras registry update --all

# Build index for local registry
sutras registry build-index <path> [--output PATH]
```

### Package and Distribute

#### Building Packages

```sh
# Build a distributable package
sutras build my-skill

# Build with custom output directory
sutras build my-skill --output ./packages

# Skip validation
sutras build my-skill --no-validate
```

Creates a versioned tarball (e.g., `my-skill-1.0.0.tar.gz`) in `dist/` containing:
- SKILL.md and sutras.yaml
- Supporting files (examples.md, etc.)
- MANIFEST.json with checksums and metadata

**Requirements for distribution:**
- Version (semver format) in sutras.yaml
- Author in sutras.yaml
- License in sutras.yaml
- Valid skill name and description
- Scoped name format: `@namespace/skill-name` (required for registry publishing)

#### Publishing to Registry

```sh
# Publish to default registry
sutras publish

# Publish to specific registry
sutras publish --registry my-registry

# Use pull request workflow (for public registries)
sutras publish --pr
```

**Publishing requirements:**
- All build requirements above
- Skill name must be scoped: `@username/skill-name`
- Registry must be configured with write access (or use --pr flag)

#### Installing Skills

Skills can be installed from multiple sources:

**From Registry:**
```sh
# Install latest version from any configured registry
sutras install @username/skill-name

# Install specific version
sutras install @username/skill-name --version 1.2.0

# Install from specific registry
sutras install @username/skill-name --registry company-registry
```

**From GitHub Releases:**
```sh
# Install latest release
sutras install github:username/repo

# Install specific version
sutras install github:username/repo@v1.0.0
sutras install github:username/repo@1.0.0
```

**From Direct URL:**
```sh
# Install from any HTTPS URL
sutras install https://example.com/skills/my-skill-1.0.0.tar.gz
sutras install https://github.com/user/repo/releases/download/v1.0.0/skill.tar.gz
```

**From Local File:**
```sh
# Install from local tarball
sutras install ./dist/my-skill-1.0.0.tar.gz
sutras install /path/to/skill.tar.gz
```

Installed skills are placed in:
- `~/.claude/installed/` - Versioned skill installations
- `~/.claude/skills/` - Symlinks to active versions

**Note:** GitHub releases and direct URL installs allow sharing skills without setting up a registry!

#### Registry Setup

```sh
# Add the official registry (example)
sutras registry add official https://github.com/anthropics/sutras-registry --default

# Add a company registry
sutras registry add company https://github.com/mycompany/skills-registry --priority 10

# Add a personal registry
sutras registry add personal https://github.com/myuser/my-skills

# Update all registry indexes
sutras registry update --all
```

**Registry features:**
- Federated Git-based design (like Homebrew taps, Go modules)
- No central infrastructure required
- Private registries via Git authentication
- Works offline with cached indexes
- Multiple registry support with priority ordering

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

See [examples/skills/](./examples/skills/) for sample skills demonstrating best practices.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Testing requirements
- PR process

#### [MIT LICENSE](./LICENSE)

# Sutras

**Devtool for creating, testing, and distributing Anthropic Agent Skills with lifecycle management.**

## What is Sutras?

**Sutras** is a comprehensive CLI and library built on top of the [Anthropic Agent Skills framework](https://platform.claude.com/docs/en/agent-sdk/skills). It provides tooling for the complete skill lifecycle — from scaffolding to distribution — with a standardized Skill ABI (Application Binary Interface) for testing, evaluation, and metadata management.

### Key Features

- **Create**: Scaffold new skills with best-practice templates and Skill ABI compliance
- **Evaluate**: Test skills with eval frameworks (Ragas, custom evaluators)
- **Test**: Run skills in isolation with mock inputs and validate outputs
- **Distribute**: Package and share skills as reusable modules
- **Discover**: Browse, search, and import skills from local and remote registries
- **Import**: Easy integration of skills into agent systems

## Why Sutras?

Working with Anthropic Skills manually involves:
- Creating SKILL.md files with proper YAML frontmatter
- Managing skill metadata and descriptions
- Testing skills across different scenarios
- Sharing skills with teams
- Ensuring skill quality and consistency

Sutras automates all of this with a unified devtool experience.

## Installation

Using pip:

```sh
pip install sutras
```

Or using uv (recommended):

```sh
uv pip install sutras
```

## Quick Start

### Creating a New Skill

Use the CLI to scaffold a new skill:

```sh
sutras new pdf-form-filler --description "Fill PDF forms automatically"
```

This creates a skill with proper Anthropic Skills structure:

```
.claude/skills/pdf-form-filler/
├── SKILL.md           # Main skill definition with YAML frontmatter
├── sutras.yaml        # Sutras ABI metadata (eval, tests, distribution)
└── examples.md        # Usage examples
```

### Skill Structure (SKILL.md)

```yaml
---
name: pdf-form-filler
description: Fill PDF forms automatically. Use when user needs to populate PDF forms with data from JSON, CSV, or manual input.
allowed-tools: Read, Write, Bash
---

# PDF Form Filler

This skill helps fill PDF forms programmatically.

## Instructions

1. Read the PDF form to identify fields
2. Map input data to form fields
3. Fill the form using appropriate tools
4. Save the completed PDF

## Examples

[See examples.md](examples.md) for detailed use cases.
```

### Using Skills with Claude

Skills are automatically discovered by Claude when using the Agent SDK:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Fill out form.pdf with data from data.json",
    options=ClaudeAgentOptions(
        cwd=".claude/skills",
        setting_sources=["project"],
        allowed_tools=["Skill", "Read", "Write", "Bash"]
    )
):
    print(message)
```

### CLI Commands

```sh
# Scaffold new skill
sutras new <name> [--description DESC] [--author AUTHOR]

# List available skills
sutras list [--local | --global]

# Show skill information
sutras info <name>

# Validate skill structure
sutras validate <name>

# Test skill (coming soon)
sutras test <name> [--input ...]

# Evaluate skill (coming soon)
sutras eval <name> [--framework ragas]

# Build skill package (coming soon)
sutras build <name>

# Publish to registry (coming soon)
sutras publish <name>

# Discover skills (coming soon)
sutras discover [--search QUERY]
```

## Core Concepts

### Skill Structure

Every Sutras-managed skill consists of:

1. **SKILL.md** - Anthropic Skills format with YAML frontmatter (required)
   - `name`: Skill identifier (lowercase, hyphens)
   - `description`: What it does and when to use it (critical for Claude discovery)
   - `allowed-tools`: Optional tool restrictions

2. **sutras.yaml** - Sutras ABI metadata (optional but recommended)
   - `version`: Semantic version
   - `author`: Skill author
   - `license`: Distribution license
   - `repository`: Source repository
   - `tests`: Test specifications
   - `eval`: Evaluation configuration

3. **Supporting files** (optional)
   - `examples.md`: Usage examples
   - `reference.md`: Detailed documentation
   - `scripts/`: Utility scripts
   - `templates/`: Reusable templates

### Skill ABI (sutras.yaml)

The `sutras.yaml` file extends Anthropic Skills with lifecycle metadata:

```yaml
version: "1.0.0"
author: "Your Name"
license: "MIT"
repository: "https://github.com/user/skill"

# Capability declarations
capabilities:
  tools: [Read, Write, Bash]
  dependencies: []
  constraints: {}

# Test configuration (optional)
tests:
  cases:
    - name: "basic-fill-test"
      inputs:
        form: "tests/fixtures/form.pdf"
        data: "tests/fixtures/data.json"
      expected:
        output_file: "tests/fixtures/expected.pdf"

# Evaluation configuration (optional)
eval:
  framework: "ragas"
  metrics: ["correctness", "completeness"]
  dataset: "tests/eval/dataset.json"

# Distribution metadata
distribution:
  tags: ["pdf", "forms", "automation"]
  category: "document-processing"
```

### Skill Lifecycle

Sutras supports the complete skill lifecycle:

1. **Create**: `sutras new` scaffolds with templates
2. **Develop**: Edit SKILL.md and supporting files
3. **Validate**: `sutras validate` checks ABI compliance
4. **Test**: `sutras test` runs unit tests (coming soon)
5. **Evaluate**: `sutras eval` measures quality (coming soon)
6. **Build**: `sutras build` packages for distribution (coming soon)
7. **Publish**: `sutras publish` shares to registry (coming soon)
8. **Discover**: `sutras discover` finds published skills (coming soon)

### Skills Directory

When you create skills with `sutras new`, they're placed in:
- **Project skills**: `.claude/skills/` (shared with team via git)
- **Global skills**: `~/.claude/skills/` (personal, not committed)

These follow the Anthropic Skills directory convention.

## Library Usage

Use Sutras as a library to integrate skill management into your applications:

```python
from sutras import SkillLoader

# Load and inspect skills
loader = SkillLoader()
skills = loader.discover()            # Find available skills
skill = loader.load("pdf-processor")  # Load specific skill

print(f"Skill: {skill.name}")
print(f"Description: {skill.description}")
print(f"Allowed tools: {skill.allowed_tools}")
print(f"Path: {skill.path}")
```

## Examples

Check out the [examples/](./examples/) directory for sample skills demonstrating best practices.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, guidelines, and workflow.

Quick development commands (requires [just](https://github.com/casey/just)):

```sh
just format     # Format code
just lint       # Lint code
just check      # Type check
just test       # Run tests
just pre-commit # Run all checks
```

## License

MIT License - see [LICENSE](./LICENSE) for details.

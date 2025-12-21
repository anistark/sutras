# Ability

**Devtool for creating, testing, and distributing Anthropic Agent Skills with lifecycle management.**

## What is Ability?

**Ability** is a comprehensive CLI and library built on top of the [Anthropic Agent Skills framework](https://platform.claude.com/docs/en/agent-sdk/skills). It provides tooling for the complete skill lifecycle — from scaffolding to distribution — with a standardized Skill ABI (Application Binary Interface) for testing, evaluation, and metadata management.

### Key Features

- **Create**: Scaffold new skills with best-practice templates and Skill ABI compliance
- **Evaluate**: Test skills with eval frameworks (Ragas, custom evaluators)
- **Test**: Run skills in isolation with mock inputs and validate outputs
- **Distribute**: Package and share skills as reusable modules
- **Discover**: Browse, search, and import skills from local and remote registries
- **Import**: Easy integration of skills into agent systems

## Why Ability?

Working with Anthropic Skills manually involves:
- Creating SKILL.md files with proper YAML frontmatter
- Managing skill metadata and descriptions
- Testing skills across different scenarios
- Sharing skills with teams
- Ensuring skill quality and consistency

Ability automates all of this with a unified devtool experience.

## Installation

Using pip:

```sh
pip install ability
```

Or using uv (recommended):

```sh
uv pip install ability
```

## Quick Start

### Creating a New Skill

Use the CLI to scaffold a new skill:

```sh
ability new pdf-form-filler --description "Fill PDF forms automatically"
```

This creates a skill with proper Anthropic Skills structure:

```
.claude/skills/pdf-form-filler/
├── SKILL.md           # Main skill definition with YAML frontmatter
├── ability.yaml       # Ability ABI metadata (eval, tests, distribution)
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
ability new <name> [--description DESC] [--author AUTHOR]

# List available skills
ability list [--local | --global]

# Show skill information
ability info <name>

# Validate skill structure
ability validate <name>

# Test skill (coming soon)
ability test <name> [--input ...]

# Evaluate skill (coming soon)
ability eval <name> [--framework ragas]

# Build skill package (coming soon)
ability build <name>

# Publish to registry (coming soon)
ability publish <name>

# Discover skills (coming soon)
ability discover [--search QUERY]
```

## Core Concepts

### Skill Structure

Every Ability-managed skill consists of:

1. **SKILL.md** - Anthropic Skills format with YAML frontmatter (required)
   - `name`: Skill identifier (lowercase, hyphens)
   - `description`: What it does and when to use it (critical for Claude discovery)
   - `allowed-tools`: Optional tool restrictions

2. **ability.yaml** - Ability ABI metadata (optional but recommended)
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

### Skill ABI (ability.yaml)

The `ability.yaml` file extends Anthropic Skills with lifecycle metadata:

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

Ability supports the complete skill lifecycle:

1. **Create**: `ability new` scaffolds with templates
2. **Develop**: Edit SKILL.md and supporting files
3. **Validate**: `ability validate` checks ABI compliance
4. **Test**: `ability test` runs unit tests (coming soon)
5. **Evaluate**: `ability eval` measures quality (coming soon)
6. **Build**: `ability build` packages for distribution (coming soon)
7. **Publish**: `ability publish` shares to registry (coming soon)
8. **Discover**: `ability discover` finds published skills (coming soon)

### Skills Directory

When you create skills with `ability new`, they're placed in:
- **Project skills**: `.claude/skills/` (shared with team via git)
- **Global skills**: `~/.claude/skills/` (personal, not committed)

These follow the Anthropic Skills directory convention.

## Library Usage

Use Ability as a library to integrate skill management into your applications:

```python
from ability import SkillLoader

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

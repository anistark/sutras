# Project Structure

Overview of the Sutras codebase organization.

## Directory Layout

```sh
sutras/
├── src/sutras/             # Main package (src layout)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── skill.py        # Skill model (SKILL.md + sutras.yaml)
│   │   ├── abi.py          # Skill ABI definitions
│   │   ├── loader.py       # Skill discovery and loading
│   │   ├── builder.py      # Skill packaging
│   │   ├── test_runner.py  # Test framework
│   │   ├── evaluator.py    # Evaluation system
│   │   ├── config.py       # Global configuration
│   │   ├── naming.py       # Skill naming system
│   │   ├── registry.py     # Registry management
│   │   ├── installer.py    # Skill installation
│   │   ├── publisher.py    # Skill publishing
│   │   ├── semver.py       # Semantic versioning and constraints
│   │   ├── lockfile.py     # Lock file management
│   │   └── resolver.py     # Dependency resolution
│   └── cli/
│       ├── __init__.py
│       └── main.py         # CLI commands
├── examples/               # Example skills
│   └── skills/
│       └── hello-claude/   # Demo skill (Anthropic format)
│           ├── SKILL.md
│           ├── sutras.yaml
│           └── examples.md
├── tests/                  # Test suite
│   └── test_skill.py
├── pyproject.toml          # Project config (hatchling + uv)
├── uv.lock                 # Locked dependencies
├── LICENSE
└── README.md
```

## Core Modules

| Module | Responsibility |
|--------|----------------|
| `skill.py` | Skill model representing SKILL.md + sutras.yaml |
| `abi.py` | Skill ABI (Application Binary Interface) definitions |
| `loader.py` | Discovering and loading skills from disk |
| `builder.py` | Building distributable packages |
| `test_runner.py` | Running skill tests |
| `evaluator.py` | Evaluating skill quality |
| `registry.py` | Managing skill registries |
| `installer.py` | Installing skills from various sources |
| `publisher.py` | Publishing skills to registries |
| `resolver.py` | Resolving skill dependencies |

## User Skills Directory

When you create skills with `sutras new`, they're placed in:

| Location | Purpose |
|----------|---------|
| `.claude/skills/` | Project skills (shared via git) |
| `~/.claude/skills/` | Global skills (personal, not committed) |

These follow the Anthropic Skills directory convention.

# Pi Integration

Sutras provides a [pi](https://github.com/badlogic/pi) extension and skill for using sutras
directly within pi's TUI. The extension registers a `/sutras` command that mirrors the full
CLI with interactive enhancements.

## Installation

### Prerequisites

The sutras Python CLI must be installed and available on your PATH:

```sh
pip install sutras
```

### Install the pi package

```sh
pi install npm:sutras
```

This installs both the extension (provides `/sutras` commands) and the skill (provides LLM
context for autonomous skill development).

Alternatively, install from git for the latest development version:

```sh
pi install git:github.com/anistark/sutras
```

## The `/sutras` Command

Once installed, all sutras commands are available under `/sutras` in pi:

```
/sutras new [name]         Create a new skill (interactive)
/sutras list               List available skills
/sutras info [name]        Show skill details
/sutras validate [name]    Validate a skill
/sutras test [name]        Run skill tests
/sutras eval [name]        Evaluate with metrics
/sutras docs [name]        Generate documentation
/sutras build [name]       Build distributable package
/sutras install <source>   Install a skill
/sutras uninstall <name>   Uninstall a skill
/sutras publish [path]     Publish to registry
/sutras registry <cmd>     Manage registries
/sutras setup              Install skill into Claude Code
```

### Interactive Features

The pi extension adds features beyond the CLI:

- **Autocomplete**: Subcommands autocomplete as you type `/sutras v` → `validate`.
- **Template picker**: `/sutras new` presents an interactive template selection dialog.
- **Skill picker**: Commands that take a skill name (`info`, `validate`, `test`, etc.) show
  a selection list of discovered skills when no name is provided.
- **Auto-validation**: Writing a `SKILL.md` or `sutras.yaml` via the write tool triggers
  background validation. The result appears in the footer status bar.
- **Availability check**: On session start, the extension verifies `sutras` is installed and
  shows the version in the footer.

### Example: Creating a Skill Interactively

```
/sutras new
```

This prompts for:
1. Skill name
2. Template (select from list)
3. Description
4. Author
5. Scope (project or global)

No arguments needed — the extension handles everything through dialogs.

## The Sutras Skill

The npm package also includes a skill (`SKILL.md`) that teaches the LLM about sutras. This
means pi's agent can autonomously:

- Create skills when asked ("make me a skill for code review")
- Validate skills it has created
- Use the correct `SKILL.md` frontmatter format
- Follow sutras best practices

The skill is loaded on-demand when the agent determines it's relevant, or explicitly via
`/skill:sutras`.

## How It Works

### Architecture

```
sutras CLI (Python)
    ↑ subprocess calls
pi extension (TypeScript)
    ↓ results
pi TUI (notifications, dialogs, status bar)
```

The extension calls `sutras` via `pi.exec()` — it does not reimplement any logic. This means
the extension always reflects the exact behavior of the installed CLI version.

### Package Structure

The npm package (`sutras`) contains:

```
sutras/
├── package.json          # Pi package manifest
├── extensions/
│   └── sutras.ts         # Extension with /sutras command
└── skills/
    └── sutras/
        └── SKILL.md      # Agent skill for LLM context
```

### Auto-Sync

The extension's subcommand list and the skill's command reference are auto-generated from
the Click CLI source using `scripts/sync_pi.py`. This ensures they never drift from the
actual CLI. CI enforces sync via `just check-sync`.

## Uninstalling

```sh
pi remove npm:sutras
```

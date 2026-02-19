# Installation

## Requirements

- Python 3.11 or higher

## Install with pip

```sh
pip install sutras
```

## Install with uv

```sh
uv pip install sutras
```

## Verify Installation

```sh
sutras --version
```

## Claude Code Integration

Deploy the sutras skill so Claude Code can create and manage skills:

```sh
sutras setup
```

This copies the bundled `SKILL.md` to `~/.claude/skills/sutras/`. The skill version always
matches the installed CLI. See [`sutras setup`](../cli/setup.md) for details.

## Pi Integration

If you use [pi](https://github.com/badlogic/pi), install the sutras extension for `/sutras`
commands with interactive UI:

```sh
pi install npm:sutras
```

See the [Pi Integration guide](../guides/pi-integration.md) for details.

## Next Steps

Once installed, head to the [Quickstart](quickstart.md) guide to create your first skill.

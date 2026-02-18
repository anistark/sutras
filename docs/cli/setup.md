# sutras setup

Install the sutras skill into Claude Code's global skills directory.

This deploys the bundled `SKILL.md` to `~/.claude/skills/sutras/`, allowing Claude Code
to discover sutras and use it for skill development tasks. The deployed skill always matches
the installed CLI version.

## Usage

```sh
sutras setup [OPTIONS]
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--check` | Show what would be installed without making changes | False |
| `--uninstall` | Remove the sutras skill from Claude Code | False |

## Examples

### Install the skill

```sh
sutras setup
```

Output:
```
✓ Sutras skill installed for Claude Code
  /Users/you/.claude/skills/sutras/SKILL.md

The skill will be available next time Claude Code starts.
```

### Preview before installing

```sh
sutras setup --check
```

### Remove the skill

```sh
sutras setup --uninstall
```

### Upgrade after updating sutras

```sh
pip install --upgrade sutras
sutras setup
```

The new `SKILL.md` overwrites the previous version, keeping the skill in sync with the CLI.

## How It Works

The `SKILL.md` is bundled as package data inside the `sutras` pip package. Running `sutras setup`
copies it to `~/.claude/skills/sutras/SKILL.md`. This means:

- The skill version always matches the CLI version — no drift.
- No network access needed — the file is already installed locally.
- Upgrading `sutras` and re-running `setup` updates the skill.

## Target Location

| File | Path |
|------|------|
| Skill definition | `~/.claude/skills/sutras/SKILL.md` |

This is the standard Claude Code global skills directory. Claude Code loads skills from this
location automatically.

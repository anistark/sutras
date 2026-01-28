# sutras uninstall

Uninstall a previously installed skill.

## Usage

```sh
sutras uninstall <skill-name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `skill-name` | Name of the skill to uninstall | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--version VERSION` | Specific version to uninstall | All versions |

## Examples

### Uninstall a skill

```sh
sutras uninstall my-skill
```

### Uninstall specific version

```sh
sutras uninstall my-skill --version 1.0.0
```

## Behavior

- Removes the skill from `~/.claude/skills/`
- Cleans up versioned installations in `~/.claude/installed/`
- If `--version` is not specified, removes all installed versions

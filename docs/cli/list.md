# sutras list

List all available skills in the workspace.

## Usage

```sh
sutras list [OPTIONS]
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--local / --no-local` | Include project skills (`.claude/skills/`) | True |
| `--global / --no-global` | Include global skills (`~/.claude/skills/`) | True |

## Examples

### List all skills

```sh
sutras list
```

### List only project skills

```sh
sutras list --no-global
```

### List only global skills

```sh
sutras list --no-local
```

## Output

Displays a table of skills with their names, versions, and locations.

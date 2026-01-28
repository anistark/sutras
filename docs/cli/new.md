# sutras new

Create a new skill with proper structure and best-practice templates.

## Usage

```sh
sutras new <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to create | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--description TEXT` | Skill description | None |
| `--author TEXT` | Skill author | None |
| `--global` | Create in global skills directory (`~/.claude/skills/`) | False (project) |

## Examples

### Create a basic skill

```sh
sutras new my-skill
```

### Create with description

```sh
sutras new my-skill --description "Automates PDF document processing"
```

### Create with author

```sh
sutras new my-skill --description "PDF processor" --author "Your Name"
```

### Create a global skill

```sh
sutras new my-skill --global
```

## Output

Creates the following structure:

```sh
.claude/skills/my-skill/
├── SKILL.md           # Skill definition with YAML frontmatter
├── sutras.yaml        # Metadata (version, author, tests, etc.)
└── examples.md        # Usage examples
```

## Skill Locations

- **Project skills**: `.claude/skills/` - Shared via git with your team
- **Global skills**: `~/.claude/skills/` - Personal, not committed to version control

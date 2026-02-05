# sutras new

Create a new skill with proper structure and best-practice templates.

## Usage

```sh
sutras new <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to create | Yes (unless `--list-templates`) |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--description TEXT` | Skill description | None |
| `--author TEXT` | Skill author | None |
| `--template TEXT` | Template to scaffold from | `default` |
| `--list-templates` | List available templates and exit | False |
| `--global` | Create in global skills directory (`~/.claude/skills/`) | False (project) |

## Templates

Templates provide pre-configured SKILL.md, sutras.yaml, and examples.md files
tailored to common skill categories.

### List available templates

```sh
sutras new --list-templates
```

### Built-in templates

| Template | Description |
|----------|-------------|
| `default` | Minimal skill scaffold with basic structure |
| `code-review` | Code review skill with diff analysis and feedback patterns |
| `api-integration` | API integration skill with request handling and error patterns |
| `data-analysis` | Data analysis skill with file processing and reporting patterns |
| `automation` | Workflow automation skill with task orchestration patterns |

## Examples

### Create a basic skill

```sh
sutras new my-skill
```

### Create from a template

```sh
sutras new my-reviewer --template code-review
```

### Create with description and template

```sh
sutras new my-api --template api-integration --description "Integrates with Stripe API"
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

The content of each file depends on the selected template.

## Skill Locations

- **Project skills**: `.claude/skills/` - Shared via git with your team
- **Global skills**: `~/.claude/skills/` - Personal, not committed to version control

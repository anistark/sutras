# sutras validate

Validate a skill's format, metadata, and quality standards.

## Usage

```sh
sutras validate <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to validate | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--strict` | Treat warnings as errors | False |

## Examples

### Basic validation

```sh
sutras validate my-skill
```

### Strict validation

```sh
sutras validate my-skill --strict
```

## Validation Checks

The validator checks:

- SKILL.md exists and has valid YAML frontmatter
- Required fields are present (name, description)
- sutras.yaml is valid (if present)
- Version follows semver format
- Skill name format is correct
- Dependencies are properly specified

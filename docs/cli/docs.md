# sutras docs

Generate documentation for a skill from its SKILL.md, sutras.yaml, and supporting files.

## Usage

```sh
sutras docs <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to generate docs for | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output PATH` / `-o` | Output file or directory (writes `<name>.md` when directory) | stdout |
| `--no-supporting` | Exclude supporting file contents (examples.md, etc.) | False |

## Examples

### Print to stdout

```sh
sutras docs my-skill
```

### Write to a file

```sh
sutras docs my-skill -o my-skill-reference.md
```

### Write to a directory

```sh
sutras docs my-skill -o docs/skills/
# Produces docs/skills/my-skill.md
```

### Without supporting files

```sh
sutras docs my-skill --no-supporting
```

## Output

Generates a Markdown document containing:

- **Title** derived from the skill name
- **Badges** for version, author, and license
- **Description** from SKILL.md frontmatter
- **Metadata table** with repository, category, tags, keywords, and links
- **Tools** required by the skill
- **Dependencies** declared in sutras.yaml
- **Instructions** from the SKILL.md body
- **Tests** table listing test cases
- **Evaluation** configuration summary
- **Supporting files** (appended markdown content from files like examples.md)

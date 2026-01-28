# sutras build

Build a distributable package for a skill.

## Usage

```sh
sutras build <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to build | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output PATH` | Output directory for the package | `dist/` |
| `--no-validate` | Skip validation before building | False |

## Examples

### Build a skill

```sh
sutras build my-skill
```

### Custom output directory

```sh
sutras build my-skill --output ./packages
```

### Skip validation

```sh
sutras build my-skill --no-validate
```

## Output

Creates a versioned tarball (e.g., `my-skill-1.0.0.tar.gz`) containing:

- `SKILL.md` - Skill definition
- `sutras.yaml` - Metadata
- Supporting files (examples.md, etc.)
- `MANIFEST.json` - Checksums and metadata

## Requirements for Distribution

To build a distributable package, your skill must have:

- **Version** in semver format (in `sutras.yaml`)
- **Author** (in `sutras.yaml`)
- **License** (in `sutras.yaml`)
- Valid skill name and description
- **Scoped name** format: `@namespace/skill-name` (required for registry publishing)

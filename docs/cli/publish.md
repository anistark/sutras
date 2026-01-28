# sutras publish

Publish a skill to a registry.

## Usage

```sh
sutras publish [PATH] [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `PATH` | Path to the skill or package | Current directory |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--registry NAME` | Target registry name | Default registry |
| `--pr` | Use pull request workflow | False |

## Examples

### Publish to default registry

```sh
sutras publish
```

### Publish to specific registry

```sh
sutras publish --registry my-registry
```

### Use pull request workflow

For public registries without direct write access:

```sh
sutras publish --pr
```

### Publish specific path

```sh
sutras publish ./dist/my-skill-1.0.0.tar.gz
```

## Publishing Requirements

- All [build requirements](build)
- Skill name must be scoped: `@username/skill-name`
- Registry must be configured with write access (or use `--pr` flag)

## Pull Request Workflow

The `--pr` flag:

1. Forks the registry repository
2. Creates a branch with your skill
3. Opens a pull request for review
4. Maintainers review and merge

This is the recommended approach for contributing to public registries.

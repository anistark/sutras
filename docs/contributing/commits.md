# Commit Guidelines

Use conventional commits for clear, consistent history.

## Format

```
<type>: <description>
```

## Types

| Type | Description |
|------|-------------|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes |
| `test:` | Adding or updating tests |
| `refactor:` | Code refactoring (no feature change) |
| `chore:` | Maintenance tasks |

## Examples

### Features

```
feat: add skill validation command
feat: support GitHub release installation
feat: add dependency resolution
```

### Bug Fixes

```
fix: handle missing sutras.yaml gracefully
fix: correct version parsing for pre-release
fix: resolve circular dependency detection
```

### Documentation

```
docs: update installation instructions
docs: add CLI reference page
docs: fix typo in quickstart
```

### Tests

```
test: add loader edge case tests
test: improve coverage for builder
```

### Refactoring

```
refactor: extract version parsing to separate module
refactor: simplify skill discovery logic
```

### Maintenance

```
chore: update dependencies
chore: fix linting warnings
chore: update CI configuration
```

## Best Practices

- Keep the first line under 72 characters
- Use imperative mood ("add" not "added")
- Be specific about what changed
- Reference issues when applicable: `fix: resolve #123`

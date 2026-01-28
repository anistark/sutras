# sutras test

Run tests defined for a skill.

## Usage

```sh
sutras test <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to test | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--verbose` | Show detailed test output | False |
| `--fail-fast` | Stop on first test failure | False |

## Examples

### Run all tests

```sh
sutras test my-skill
```

### Verbose output

```sh
sutras test my-skill --verbose
```

### Stop on first failure

```sh
sutras test my-skill --fail-fast
```

### Combine options

```sh
sutras test my-skill --verbose --fail-fast
```

## Test Configuration

Tests are configured in `sutras.yaml`:

```yaml
tests:
  - name: "Basic functionality"
    input: "Test input"
    expected: "Expected output"
```

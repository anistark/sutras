# sutras eval

Evaluate a skill with metrics and quality analysis.

## Usage

```sh
sutras eval <name> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Name of the skill to evaluate | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--verbose` | Show detailed evaluation output | False |
| `--no-history` | Don't save evaluation results | False |
| `--show-history` | Show previous evaluation results | False |

## Examples

### Basic evaluation

```sh
sutras eval my-skill
```

### Verbose output

```sh
sutras eval my-skill --verbose
```

### Skip saving history

```sh
sutras eval my-skill --no-history
```

### View evaluation history

```sh
sutras eval my-skill --show-history
```

## Metrics

Evaluation includes metrics such as:

- Clarity of instructions
- Completeness of examples
- Metadata quality
- Best practice adherence

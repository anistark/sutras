# Development Workflow

Common commands and workflows for developing Sutras.

## Quick Commands

### Using just (Recommended)

```sh
just --list        # Show all commands
just format        # Format code
just lint          # Lint code
just fix           # Auto-fix linting issues
just check         # Type check
just test          # Run tests
just test-cov      # Tests with coverage
just pre-commit    # Run all checks
just build         # Build package
```

### Manual Commands (uv run)

All `just` commands can also be run manually with `uv run`.

## Running Tests

```sh
uv run pytest                                    # All tests
uv run pytest --cov=sutras --cov-report=html     # With coverage
uv run pytest tests/test_skill.py                # Specific file
uv run pytest -v                                 # Verbose
```

## Code Quality

```sh
uv run ruff format src/                 # Format
uv run ruff check src/                  # Lint
uv run ruff check --fix src/            # Auto-fix
uv run ty check src/                    # Type check
```

## Testing the CLI

```sh
uv run sutras --help
uv run sutras new test-skill
uv run sutras list
uv run sutras info test-skill
uv run sutras validate test-skill
uv run sutras test test-skill
uv run sutras eval test-skill
uv run sutras build test-skill

# Registry commands
uv run sutras registry list
uv run sutras registry add test-registry https://github.com/user/registry
uv run sutras install @username/skill-name
uv run sutras publish
```

## Building

```sh
uv build  # Creates dist/ with wheel and sdist
```

## Before Submitting

Always run all checks before submitting a PR:

```sh
just pre-commit
```

Or manually:

```sh
uv run ruff format src/
uv run ruff check src/
uv run ty check src/
uv run pytest
```

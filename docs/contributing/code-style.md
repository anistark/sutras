# Code Style

Formatting and coding conventions for Sutras.

## General Guidelines

- **PEP 8** compliance
- **Type hints** for all function signatures
- **Max line length**: 100 characters
- **Docstrings**: Google-style for public APIs
- **Formatting**: Use `ruff format`

## Type Hints

All functions must have type hints:

```python
def load_skill(name: str, version: str | None = None) -> Skill:
    """Load a skill by name and optional version."""
    ...
```

## Docstrings

Use Google-style docstrings for public APIs:

```python
def load_skill(name: str, version: str | None = None) -> Skill:
    """Load a skill by name and optional version.

    Args:
        name: Skill identifier
        version: Semantic version (optional)

    Returns:
        Loaded Skill instance

    Raises:
        FileNotFoundError: Skill not found
    """
    ...
```

## Formatting

Format code with ruff:

```sh
uv run ruff format src/
```

## Linting

Check for issues:

```sh
uv run ruff check src/
```

Auto-fix issues:

```sh
uv run ruff check --fix src/
```

## Type Checking

```sh
uv run ty check src/
```

## Import Order

Ruff handles import ordering automatically. The general order is:

1. Standard library imports
2. Third-party imports
3. Local imports

Each group separated by a blank line.

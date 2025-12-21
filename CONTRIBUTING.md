# Contributing to Sutras

Thank you for your interest in contributing to Sutras! This document provides guidelines and information for contributors.

## Development Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and [hatchling](https://hatch.pypa.io/) for building.

### Prerequisites

- Python 3.11 or higher
- uv (install from https://github.com/astral-sh/uv)
- just (optional, for convenient task running - install from https://github.com/casey/just)

### Setup

```sh
# Fork the repo

# Clone the repository or add upstream if you've forked it
git clone https://github.com/anistark/sutras.git
cd sutras

# Install dependencies and create virtual environment
uv sync

# Activate the virtual environment (optional, uv run handles this)
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

## Project Structure

```sh
sutras/
├── src/sutras/             # Main package (src layout)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── skill.py        # Skill model (SKILL.md + sutras.yaml)
│   │   ├── abi.py          # Skill ABI definitions
│   │   └── loader.py       # Skill discovery and loading
│   └── cli/
│       ├── __init__.py
│       └── main.py         # CLI commands
├── examples/               # Example skills
│   └── skills/
│       └── hello-claude/   # Demo skill (Anthropic format)
│           ├── SKILL.md
│           ├── sutras.yaml
│           └── examples.md
├── tests/                  # Test suite
│   └── test_skill.py
├── pyproject.toml          # Project config (hatchling + uv)
├── uv.lock                 # Locked dependencies
├── LICENSE
└── README.md
```

### User Skills Directory

When you create skills with `sutras new`, they're placed in:
- **Project skills**: `.claude/skills/` (shared with team via git)
- **Global skills**: `~/.claude/skills/` (personal, not committed)

These follow the Anthropic Skills directory convention.

## Quick Commands with just (Optional)

We provide a `justfile` for convenient task running. If you have [just](https://github.com/casey/just) installed, you can use these shortcuts:

```sh
# View all available commands
just --list

# Format code
just format

# Lint code
just lint

# Fix linting issues
just fix

# Type check
just check

# Run all quality checks (format, lint, check)
just qa

# Run tests
just test

# Run tests with coverage
just test-cov

# Run all checks before commit
just pre-commit

# Build distribution
just build

# Clean build artifacts
just clean
```

All commands can also be run manually with `uv run` (see below).

## Development Workflow

### Running Tests

```sh
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=sutras --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_skill.py

# Run tests in verbose mode
uv run pytest -v
```

### Code Quality

```sh
# Format code
uv run ruff format src/sutras/

# Lint code
uv run ruff check src/sutras/

# Fix linting issues automatically
uv run ruff check --fix src/sutras/

# Type checking (using Astral's ty)
uv run ty check src/sutras/
```

### Running the CLI

```sh
# Run the CLI directly
uv run sutras --help

# Test specific commands
uv run sutras new test-skill
uv run sutras list
uv run sutras info test-skill
uv run sutras validate test-skill
```

### Building

```sh
# Build distribution packages
uv build

# This creates wheel and sdist in dist/
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use ruff for formatting and linting
- Write docstrings for all public functions and classes

### Type Hints

```python
from typing import Optional, List, Dict, Any

def load_skill(name: str, version: Optional[str] = None) -> Skill:
    """Load a skill by name and optional version."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def create_skill(name: str, description: str) -> Skill:
    """Create a new skill with the given name and description.

    Args:
        name: The skill name (lowercase, hyphens allowed)
        description: What the skill does and when to use it

    Returns:
        The created Skill instance

    Raises:
        ValueError: If name is invalid or skill already exists
    """
    ...
```

## Testing Guidelines

- Write tests for all new features
- Aim for high test coverage (>80%)
- Use pytest fixtures for common test setups
- Test edge cases and error conditions
- Keep tests focused and readable

### Test Structure

```python
def test_skill_loading():
    """Test that skills load correctly."""
    # Arrange
    skill_dir = create_test_skill()

    # Act
    loader = SkillLoader(search_paths=[skill_dir])
    skill = loader.load("test-skill")

    # Assert
    assert skill.name == "test-skill"
    assert skill.version == "1.0.0"
```

## Commit Guidelines

- Write clear, descriptive commit messages
- Use conventional commits format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `test:` for test additions/changes
  - `refactor:` for code refactoring
  - `chore:` for maintenance tasks

### Example Commits

```sh
feat: add skill validation command
fix: handle missing sutras.yaml gracefully
docs: update installation instructions
test: add tests for skill loader
refactor: simplify ABI parsing logic
chore: update dependencies
```

## Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Add tests** for new functionality
4. **Run tests and linting** to ensure everything passes
5. **Update documentation** if needed (README, docstrings, etc.)
6. **Submit a pull request** with a clear description of changes

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] No new warnings generated
```

## Adding New Features

### Adding a New CLI Command

1. Add the command to `src/sutras/cli/main.py`
2. Follow the Click framework conventions
3. Add comprehensive help text
4. Handle errors gracefully
5. Add tests for the command

Example:

```python
@cli.command()
@click.argument("name")
@click.option("--option", help="Description")
def new_command(name: str, option: Optional[str]) -> None:
    """Brief description of what this command does."""
    try:
        # Implementation
        click.echo(f"Success!")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
```

### Adding New Core Functionality

1. Add implementation in appropriate `src/sutras/core/` module
2. Add type hints and docstrings
3. Export from `__init__.py` if public API
4. Add comprehensive tests
5. Update documentation

## Questions or Issues?

- Open an issue on GitHub for bugs or feature requests
- Check existing issues before creating new ones
- Provide clear reproduction steps for bugs
- Include relevant code snippets and error messages

## License

By contributing to Sutras, you agree that your contributions will be licensed under the MIT License.

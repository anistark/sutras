# Contributing

Thank you for contributing to Sutras! This guide covers development setup, workflow, and guidelines.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [just](https://github.com/casey/just) (optional) - Task runner

### Initial Setup

```sh
# Clone your fork
git clone https://github.com/<your-username>/sutras.git
cd sutras

# Install dependencies
uv sync

# Optional: activate virtual environment
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

The project uses:
- **uv** - Dependency management and virtual environments
- **hatchling** - Build backend
- **ruff** - Linting and formatting
- **ty** - Type checking
- **pytest** - Testing

## Project Structure

```sh
sutras/
├── src/sutras/             # Main package (src layout)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── skill.py        # Skill model (SKILL.md + sutras.yaml)
│   │   ├── abi.py          # Skill ABI definitions
│   │   ├── loader.py       # Skill discovery and loading
│   │   ├── builder.py      # Skill packaging
│   │   ├── test_runner.py  # Test framework
│   │   ├── evaluator.py    # Evaluation system
│   │   ├── config.py       # Global configuration
│   │   ├── naming.py       # Skill naming system
│   │   ├── registry.py     # Registry management
│   │   ├── installer.py    # Skill installation
│   │   ├── publisher.py    # Skill publishing
│   │   ├── semver.py       # Semantic versioning and constraints
│   │   ├── lockfile.py     # Lock file management
│   │   └── resolver.py     # Dependency resolution
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

## Development Workflow

### Running Tests

```sh
uv run pytest                                    # All tests
uv run pytest --cov=sutras --cov-report=html     # With coverage
uv run pytest tests/test_skill.py                # Specific file
uv run pytest -v                                 # Verbose
```

### Code Quality

```sh
uv run ruff format src/                 # Format
uv run ruff check src/                  # Lint
uv run ruff check --fix src/            # Auto-fix
uv run ty check src/                    # Type check
```

### Testing the CLI

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

### Building

```sh
uv build  # Creates dist/ with wheel and sdist
```

## Code Style

- **PEP 8** compliance
- **Type hints** for all function signatures
- **Max line length**: 100 characters
- **Docstrings**: Google-style for public APIs
- **Formatting**: Use `ruff format`

### Example

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

## Testing Guidelines

- Write tests for new features
- Target >80% coverage
- Use pytest fixtures
- Test edge cases and errors
- Follow Arrange-Act-Assert pattern

```python
def test_skill_loading(tmp_path):
    """Test skill loading."""
    # Arrange
    skill_dir = tmp_path / "test-skill"
    create_test_skill(skill_dir)

    # Act
    loader = SkillLoader()
    skill = loader.load("test-skill")

    # Assert
    assert skill.name == "test-skill"
```

## Commit Guidelines

Use conventional commits:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

**Examples:**

```
feat: add skill validation command
fix: handle missing sutras.yaml gracefully
docs: update installation instructions
```

## Pull Request Process

1. Fork and create branch from `main`
2. Make changes following style guidelines
3. Add tests for new features
4. Run `just pre-commit` (or all checks manually)
5. Update docs if needed
6. Submit PR with clear description

### PR Checklist

- [ ] Tests pass (`just test`)
- [ ] Code formatted (`just format`)
- [ ] Linting passes (`just lint`)
- [ ] Type checking passes (`just check`)
- [ ] Documentation updated
- [ ] Changelog entry (if applicable)

## Adding Features

### New CLI Command

Add to `src/sutras/cli/main.py`:

```python
@cli.command()
@click.argument("name")
@click.option("--flag", help="Description")
def command(name: str, flag: bool) -> None:
    """Command description."""
    try:
        # Implementation
        click.echo(click.style("Success", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        raise click.Abort()
```

### New Core Feature

1. Add to `src/sutras/core/`
2. Include type hints and docstrings
3. Export from `__init__.py` if public
4. Add tests
5. Update docs

## Questions?

- Check [existing issues](https://github.com/anistark/sutras/issues)
- Open new issue with reproduction steps
- Include error messages and code snippets

## License

Contributions licensed under MIT License.

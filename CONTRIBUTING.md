# Contributing to Sutras

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
│   │   └── publisher.py    # Skill publishing
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
        click.echo(click.style("✓ Success", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        raise click.Abort()
```

### New Core Feature

1. Add to `src/sutras/core/`
2. Include type hints and docstrings
3. Export from `__init__.py` if public
4. Add tests
5. Update docs

## Packaging Skills

### Building Distribution Packages

Skills can be packaged for distribution using `sutras build`:

```sh
sutras build my-skill            # Creates dist/my-skill-1.0.0.tar.gz
sutras build my-skill -o ./pkg   # Custom output directory
```

### Package Requirements

For a skill to be buildable, `sutras.yaml` must include:

```yaml
version: "1.0.0"      # Semantic versioning (required)
author: "Your Name"   # Author name (required)
license: "MIT"        # License identifier (required)
```

Version format must follow semver: `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`

Examples:
- `1.0.0` - Standard release
- `1.0.0-beta` - Pre-release
- `1.0.0+20240101` - With build metadata

### Package Contents

Built packages include:
- `SKILL.md` - Skill definition
- `sutras.yaml` - Metadata
- Supporting files (`examples.md`, etc.)
- `MANIFEST.json` - File checksums and package metadata

### Testing Packaging

When developing packaging features:

```sh
# Create test skill
uv run sutras new test-pkg --author "Test" --description "Testing packaging"

# Add version to sutras.yaml
echo 'version: "0.1.0"' >> .claude/skills/test-pkg/sutras.yaml
echo 'license: "MIT"' >> .claude/skills/test-pkg/sutras.yaml

# Build package
uv run sutras build test-pkg

# Verify package
tar -tzf dist/test-pkg-0.1.0.tar.gz
```

## Registry System Development

### Architecture

The registry system uses a federated Git-based design:

- **Configuration**: `~/.sutras/config.yaml` stores registry configurations
- **Caching**: `~/.sutras/registry-cache/` holds cloned registry repos
- **Installation**: `~/.claude/installed/` stores versioned skills
- **Symlinks**: `~/.claude/skills/` provides active skill links

### Core Components

1. **Config** (`config.py`): Global configuration management
2. **Naming** (`naming.py`): Skill name parsing with namespace support
3. **Registry** (`registry.py`): Multi-registry management and index parsing
4. **Installer** (`installer.py`): Download, verify, and install skills
5. **Publisher** (`publisher.py`): Build and publish to registries

### Testing Registry Features

#### Setting Up a Test Registry

```sh
# Create a local test registry
mkdir -p /tmp/test-registry/skills
cd /tmp/test-registry

# Initialize git repo
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Create registry metadata
cat > registry.yaml << EOF
name: test-registry
description: Test registry for development
visibility: public
EOF

# Commit
git add .
git commit -m "Initial registry setup"
```

#### Creating a Test Skill for Publishing

```sh
# Create skill with scoped name (required for publishing)
cd /tmp
uv run sutras new @testuser/demo-skill --author "Test User" --description "Demo skill"

# Update to use scoped name in SKILL.md
cd .claude/skills/@testuser/demo-skill
# Edit SKILL.md to change name: @testuser/demo-skill

# Ensure sutras.yaml has required fields
cat >> sutras.yaml << EOF
version: "0.1.0"
author: "Test User"
license: "MIT"
EOF

# Build the package
cd /tmp
uv run sutras build .claude/skills/@testuser/demo-skill
```

#### Testing Registry Commands

```sh
# Add test registry
uv run sutras registry add test-local file:///tmp/test-registry --default

# List registries
uv run sutras registry list

# Build index for the registry
uv run sutras registry build-index /tmp/test-registry

# Update registry cache
uv run sutras registry update test-local

# Publish skill (requires skill to exist)
cd .claude/skills/@testuser/demo-skill
uv run sutras publish --registry test-local

# Install skill
uv run sutras install @testuser/demo-skill --registry test-local

# List installed
ls ~/.claude/installed/

# Uninstall
uv run sutras uninstall @testuser/demo-skill

# Remove registry
uv run sutras registry remove test-local
```

#### Testing with Remote Git Registry

```sh
# Create a test repo on GitHub/GitLab
# Then add it as a registry
uv run sutras registry add remote-test https://github.com/username/test-registry

# Update to fetch the index
uv run sutras registry update remote-test

# Install from remote
uv run sutras install @namespace/skill-name --registry remote-test
```

### Naming Conventions

- **Scoped names**: Required for registry publishing: `@namespace/skill-name`
- **Bare names**: Only for local development: `skill-name`
- **Namespace**: Must match Git username/org in registry configuration
- **Validation**: Uses regex `^[a-zA-Z0-9_-]+$` for both namespace and name

### Index Schema

Registry `index.yaml` format:

```yaml
version: "1.0"
skills:
  "@username/skill-name":
    name: "@username/skill-name"
    version: "1.0.0"
    description: "Skill description"
    author: "Author Name"
    tarball_url: "skills/@username/skill-name/skill-name-1.0.0.tar.gz"
    checksum: "sha256-hash-here"
    versions:
      "1.0.0": "skills/@username/skill-name/skill-name-1.0.0.tar.gz"
```

### Common Development Tasks

**Adding a new registry feature:**
1. Update appropriate core module (`registry.py`, `installer.py`, etc.)
2. Add CLI command in `main.py`
3. Add tests
4. Update documentation (README, CONTRIBUTING)
5. Add changelog entry

**Testing error handling:**
- Missing registry
- Invalid skill name format
- Network failures (use local file:// repos)
- Checksum mismatches
- Missing required fields in sutras.yaml

## Questions?

- Check [existing issues](https://github.com/anistark/sutras/issues)
- Open new issue with reproduction steps
- Include error messages and code snippets

## License

Contributions licensed under MIT License.

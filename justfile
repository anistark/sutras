# Sutras - Development Commands
# https://github.com/casey/just

# Default recipe to display help
default:
    @just --list

# Format code with ruff
format:
    uv run ruff format src/sutras/ tests/

# Lint code with ruff
lint:
    uv run ruff check src/sutras/ tests/

# Fix linting issues automatically
fix:
    uv run ruff check --fix src/sutras/ tests/

# Type check with ty
check:
    uv run ty check src/sutras/

# Run all quality checks (format, lint, type check)
qa: format lint check

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=sutras --cov-report=term-missing

# Run tests in verbose mode
test-verbose:
    uv run pytest -v

# Build distribution packages
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Run the CLI with --help
run:
    uv run sutras --help

# Run the CLI with custom args (usage: just run-with "list")
run-with *ARGS:
    uv run sutras {{ARGS}}

# Install in development mode
install:
    uv sync

# Publish to PyPI (requires credentials)
publish: clean build
    @echo "🔨 Building package..."
    uv build --sdist --wheel
    @echo "📦 Publishing to PyPI..."
    uv run twine upload dist/*

# Publish to Test PyPI
publish-test: clean build
    uv publish --publish-url https://test.pypi.org/legacy/

# Run all checks before commit
pre-commit: qa test
    @echo "✓ All checks passed! Ready to commit."

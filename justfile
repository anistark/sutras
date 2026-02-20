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
    uv run python -m pytest

# Run tests with coverage
test-cov:
    uv run python -m pytest --cov=sutras --cov-report=term-missing

# Run tests in verbose mode
test-verbose:
    uv run python -m pytest -v

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

# Run sutras from dev state (usage: just sutras list, just sutras install @foo/bar)
sutras *ARGS:
    uv run sutras {{ARGS}}

# Install in development mode
install:
    uv sync

# Check that pyproject.toml and pi/package.json versions match
check-versions:
    #!/usr/bin/env bash
    pypi_ver=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
    npm_ver=$(grep '"version"' pi/package.json | sed 's/.*"\([0-9][^"]*\)".*/\1/')
    if [ "$pypi_ver" != "$npm_ver" ]; then
        echo "❌ Version mismatch: pyproject.toml=$pypi_ver, pi/package.json=$npm_ver"
        exit 1
    fi
    echo "✓ Versions in sync: $pypi_ver"

# Publish everything (PyPI + npm)
publish: check-versions publish-pypi publish-npm

# Publish CLI to PyPI (requires credentials in ~/.pypirc)
publish-pypi: clean build
    @echo "🔨 Building package..."
    uv build --sdist --wheel
    @echo "📦 Publishing to PyPI..."
    uv publish --token "$(grep -A2 '\[pypi\]' ~/.pypirc | grep password | cut -d'=' -f2- | xargs)"

# Publish pi extension to npm
publish-npm:
    @echo "📦 Publishing pi extension to npm..."
    cd pi && pnpm publish

# Publish to Test PyPI + dry-run npm
publish-test: check-versions clean build
    @echo "🔨 Building package..."
    uv build --sdist --wheel
    @echo "📦 Publishing to Test PyPI..."
    uv publish --publish-url https://test.pypi.org/legacy/
    @echo "📦 Dry-run npm publish..."
    cd pi && pnpm publish --dry-run --no-git-checks

# Sync pi extension + skill from CLI introspection
sync-pi:
    uv run python scripts/sync_pi.py

# Check pi files are in sync (CI)
check-sync:
    uv run python scripts/sync_pi.py --check

# Run all checks before commit
pre-commit: qa test check-sync
    @echo "✓ All checks passed! Ready to commit."

# Build documentation
docs-build:
    uv run --extra docs sphinx-build -b dirhtml docs docs/_build/html

# Serve documentation with live reload
docs-serve:
    uv run --extra docs sphinx-autobuild -b dirhtml docs docs/_build/html --port 8000

# Clean documentation build
docs-clean:
    rm -rf docs/_build

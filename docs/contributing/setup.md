# Development Setup

Get your development environment ready to contribute to Sutras.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [just](https://github.com/casey/just) (optional) - Task runner

## Initial Setup

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

## Tools Used

| Tool | Purpose |
|------|---------|
| **uv** | Dependency management and virtual environments |
| **hatchling** | Build backend |
| **ruff** | Linting and formatting |
| **ty** | Type checking |
| **pytest** | Testing |

## Verify Setup

```sh
# Check CLI works
uv run sutras --help

# Run tests
uv run pytest

# Check all tools
just pre-commit  # or run each check manually
```

## Next Steps

- Learn the [Project Structure](structure.md)
- Review the [Development Workflow](workflow.md)

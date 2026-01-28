# Testing

Guidelines for writing and running tests.

## Running Tests

```sh
# All tests
uv run pytest

# With coverage
uv run pytest --cov=sutras --cov-report=html

# Specific file
uv run pytest tests/test_skill.py

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

## Coverage Target

Target **>80%** code coverage for new features.

## Writing Tests

### Use pytest Fixtures

```python
import pytest

@pytest.fixture
def tmp_skill(tmp_path):
    """Create a temporary skill for testing."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    # ... setup skill files
    return skill_dir
```

### Follow Arrange-Act-Assert

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

### Test Edge Cases

- Empty inputs
- Invalid data
- Missing files
- Malformed YAML

### Test Error Handling

```python
def test_missing_skill_raises():
    """Test that missing skill raises FileNotFoundError."""
    loader = SkillLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent-skill")
```

## Test Organization

```
tests/
├── test_skill.py        # Skill model tests
├── test_loader.py       # Loader tests
├── test_builder.py      # Builder tests
├── test_cli.py          # CLI tests
└── conftest.py          # Shared fixtures
```

## Using just

```sh
just test          # Run tests
just test-cov      # With coverage report
```

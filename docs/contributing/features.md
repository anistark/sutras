# Adding Features

How to add new functionality to Sutras.

## New CLI Command

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

### CLI Checklist

- [ ] Add command with `@cli.command()`
- [ ] Use type hints for all parameters
- [ ] Add docstring (shown in `--help`)
- [ ] Handle errors with colored output
- [ ] Add tests for the command
- [ ] Document in CLI reference

## New Core Feature

1. **Create module** in `src/sutras/core/`
2. **Include type hints** and docstrings
3. **Export** from `__init__.py` if public
4. **Add tests** in `tests/`
5. **Update docs** as needed

### Example Module

```python
# src/sutras/core/myfeature.py
"""My feature module."""

from dataclasses import dataclass


@dataclass
class MyFeature:
    """Represents my feature.

    Args:
        name: Feature name
        enabled: Whether feature is enabled
    """

    name: str
    enabled: bool = True

    def process(self) -> str:
        """Process the feature.

        Returns:
            Processed result string
        """
        if not self.enabled:
            raise ValueError("Feature is disabled")
        return f"Processed: {self.name}"
```

### Export Public API

In `src/sutras/core/__init__.py`:

```python
from sutras.core.myfeature import MyFeature

__all__ = [
    "MyFeature",
    # ... other exports
]
```

## Testing New Features

```python
# tests/test_myfeature.py
import pytest
from sutras.core.myfeature import MyFeature


def test_process_enabled():
    """Test processing when enabled."""
    feature = MyFeature(name="test")
    result = feature.process()
    assert result == "Processed: test"


def test_process_disabled_raises():
    """Test that disabled feature raises."""
    feature = MyFeature(name="test", enabled=False)
    with pytest.raises(ValueError):
        feature.process()
```

## Documentation

For significant features:

1. Update relevant docs pages
2. Add examples if applicable
3. Update CHANGELOG.md

"""Tests for version handling."""

import re

from sutras import __version__


def test_version_format():
    """Test that version follows semantic versioning."""
    # Should match semver format: major.minor.patch or major.minor.patch.dev0
    pattern = r"^\d+\.\d+\.\d+(?:\.dev\d+)?$"
    assert re.match(pattern, __version__), f"Version {__version__} doesn't match semver format"


def test_version_accessible():
    """Test that version is accessible from package."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0

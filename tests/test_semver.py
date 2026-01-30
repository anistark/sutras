"""Tests for semantic versioning and constraint parsing."""

import pytest

from sutras.core.semver import (
    Version,
    VersionRange,
    matches_constraint,
    parse_constraint,
    parse_version,
    select_version,
)


class TestVersion:
    def test_parse_simple(self):
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None

    def test_parse_with_prerelease(self):
        v = Version.parse("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_parse_strips_v_prefix(self):
        v = Version.parse("v1.2.3")
        assert v.major == 1

    def test_parse_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("1.2")

    def test_parse_invalid_string(self):
        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("not-a-version")

    def test_str_simple(self):
        v = Version(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_str_with_prerelease(self):
        v = Version(1, 0, 0, "beta")
        assert str(v) == "1.0.0-beta"

    def test_equality(self):
        assert Version(1, 2, 3) == Version(1, 2, 3)
        assert Version(1, 2, 3) != Version(1, 2, 4)

    def test_comparison_major(self):
        assert Version(1, 0, 0) < Version(2, 0, 0)
        assert Version(2, 0, 0) > Version(1, 0, 0)

    def test_comparison_minor(self):
        assert Version(1, 1, 0) < Version(1, 2, 0)

    def test_comparison_patch(self):
        assert Version(1, 1, 1) < Version(1, 1, 2)

    def test_comparison_prerelease(self):
        assert Version(1, 0, 0, "alpha") < Version(1, 0, 0)
        assert Version(1, 0, 0, "alpha") < Version(1, 0, 0, "beta")

    def test_hash(self):
        v1 = Version(1, 2, 3)
        v2 = Version(1, 2, 3)
        assert hash(v1) == hash(v2)


class TestVersionRange:
    def test_parse_wildcard_star(self):
        r = VersionRange.parse("*")
        assert r.matches(Version(0, 0, 0))
        assert r.matches(Version(99, 99, 99))

    def test_parse_empty(self):
        r = VersionRange.parse("")
        assert r.matches(Version(1, 0, 0))

    def test_parse_exact(self):
        r = VersionRange.parse("1.0.0")
        assert r.matches(Version(1, 0, 0))
        assert not r.matches(Version(1, 0, 1))

    def test_parse_caret_major(self):
        r = VersionRange.parse("^1.0.0")
        assert r.matches(Version(1, 0, 0))
        assert r.matches(Version(1, 9, 9))
        assert not r.matches(Version(2, 0, 0))
        assert not r.matches(Version(0, 9, 9))

    def test_parse_caret_zero_major(self):
        r = VersionRange.parse("^0.1.0")
        assert r.matches(Version(0, 1, 0))
        assert r.matches(Version(0, 1, 9))
        assert not r.matches(Version(0, 2, 0))

    def test_parse_caret_zero_minor(self):
        r = VersionRange.parse("^0.0.1")
        assert r.matches(Version(0, 0, 1))
        assert not r.matches(Version(0, 0, 2))

    def test_parse_tilde(self):
        r = VersionRange.parse("~1.2.3")
        assert r.matches(Version(1, 2, 3))
        assert r.matches(Version(1, 2, 9))
        assert not r.matches(Version(1, 3, 0))

    def test_parse_gte(self):
        r = VersionRange.parse(">=1.0.0")
        assert r.matches(Version(1, 0, 0))
        assert r.matches(Version(2, 0, 0))
        assert not r.matches(Version(0, 9, 9))

    def test_parse_lt(self):
        r = VersionRange.parse("<2.0.0")
        assert r.matches(Version(1, 9, 9))
        assert not r.matches(Version(2, 0, 0))

    def test_parse_range(self):
        r = VersionRange.parse(">=1.0.0 <2.0.0")
        assert r.matches(Version(1, 0, 0))
        assert r.matches(Version(1, 9, 9))
        assert not r.matches(Version(0, 9, 9))
        assert not r.matches(Version(2, 0, 0))

    def test_parse_wildcard_major(self):
        r = VersionRange.parse("1.x")
        assert r.matches(Version(1, 0, 0))
        assert r.matches(Version(1, 9, 9))
        assert not r.matches(Version(2, 0, 0))

    def test_parse_wildcard_minor(self):
        r = VersionRange.parse("1.2.x")
        assert r.matches(Version(1, 2, 0))
        assert r.matches(Version(1, 2, 9))
        assert not r.matches(Version(1, 3, 0))

    def test_parse_wildcard_asterisk(self):
        r = VersionRange.parse("1.*")
        assert r.matches(Version(1, 0, 0))
        assert not r.matches(Version(2, 0, 0))

    def test_select_highest(self):
        r = VersionRange.parse("^1.0.0")
        versions = [
            Version(0, 9, 0),
            Version(1, 0, 0),
            Version(1, 5, 0),
            Version(2, 0, 0),
        ]
        assert r.select_highest(versions) == Version(1, 5, 0)

    def test_select_highest_no_match(self):
        r = VersionRange.parse("^3.0.0")
        versions = [Version(1, 0, 0), Version(2, 0, 0)]
        assert r.select_highest(versions) is None

    def test_str(self):
        r = VersionRange.parse("^1.0.0")
        assert "1.0.0" in str(r)


class TestConvenienceFunctions:
    def test_parse_version(self):
        v = parse_version("1.2.3")
        assert v == Version(1, 2, 3)

    def test_parse_constraint(self):
        c = parse_constraint("^1.0.0")
        assert c.matches(Version(1, 5, 0))

    def test_matches_constraint_strings(self):
        assert matches_constraint("1.5.0", "^1.0.0")
        assert not matches_constraint("2.0.0", "^1.0.0")

    def test_matches_constraint_objects(self):
        v = Version(1, 5, 0)
        c = VersionRange.parse("^1.0.0")
        assert matches_constraint(v, c)

    def test_select_version_strings(self):
        versions = ["1.0.0", "1.5.0", "2.0.0"]
        result = select_version(versions, "^1.0.0")
        assert result == "1.5.0"

    def test_select_version_no_match(self):
        versions = ["1.0.0", "2.0.0"]
        result = select_version(versions, "^3.0.0")
        assert result is None

    def test_select_version_ignores_invalid(self):
        versions = ["1.0.0", "invalid", "1.5.0"]
        result = select_version(versions, "^1.0.0")
        assert result == "1.5.0"

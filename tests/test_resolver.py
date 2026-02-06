"""Tests for dependency resolution."""

from sutras.core.resolver import (
    CircularDependencyError,
    DependencyConflictError,
    DependencyRequest,
    DependencyResolver,
    NoMatchingVersionError,
    ResolvedSkill,
    SkillNotFoundError,
)


class TestResolvedSkill:
    def test_create(self):
        skill = ResolvedSkill(
            name="@user/skill",
            version="1.0.0",
            registry="official",
            tarball_url="https://example.com/skill.tar.gz",
            checksum="abc123",
            dependencies=["@utils/helper"],
        )
        assert skill.name == "@user/skill"
        assert skill.version == "1.0.0"
        assert skill.registry == "official"
        assert skill.dependencies == ["@utils/helper"]


class TestDependencyRequest:
    def test_create_minimal(self):
        req = DependencyRequest(name="@user/skill", constraint="^1.0.0", source="root")
        assert req.name == "@user/skill"
        assert req.constraint == "^1.0.0"
        assert req.source == "root"
        assert req.registry is None
        assert req.optional is False

    def test_create_full(self):
        req = DependencyRequest(
            name="@user/skill",
            constraint=">=1.0.0 <2.0.0",
            source="@parent/skill",
            registry="company",
            optional=True,
        )
        assert req.registry == "company"
        assert req.optional is True


class TestExceptions:
    def test_dependency_conflict_error(self):
        error = DependencyConflictError(
            "@user/skill",
            [("root", "^1.0.0"), ("@other/skill", "^2.0.0")],
        )
        assert "@user/skill" in str(error)
        assert "^1.0.0" in str(error)
        assert "^2.0.0" in str(error)

    def test_circular_dependency_error(self):
        error = CircularDependencyError(["a", "b", "c"])
        assert "a -> b -> c -> a" in str(error)

    def test_skill_not_found_error(self):
        error = SkillNotFoundError("@user/skill")
        assert "@user/skill" in str(error)
        assert "not found" in str(error)

    def test_skill_not_found_error_with_constraint(self):
        error = SkillNotFoundError("@user/skill", "^1.0.0")
        assert "@user/skill" in str(error)
        assert "^1.0.0" in str(error)

    def test_no_matching_version_error(self):
        error = NoMatchingVersionError("@user/skill", "^3.0.0", ["1.0.0", "2.0.0"])
        assert "@user/skill" in str(error)
        assert "^3.0.0" in str(error)
        assert "1.0.0" in str(error)


class TestDependencyResolver:
    def test_version_matches_exact(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        assert resolver._version_matches("1.0.0", "1.0.0")
        assert not resolver._version_matches("1.0.1", "1.0.0")

    def test_version_matches_caret(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        assert resolver._version_matches("1.5.0", "^1.0.0")
        assert not resolver._version_matches("2.0.0", "^1.0.0")

    def test_version_matches_tilde(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        assert resolver._version_matches("1.2.5", "~1.2.0")
        assert not resolver._version_matches("1.3.0", "~1.2.0")

    def test_version_matches_range(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        assert resolver._version_matches("1.5.0", ">=1.0.0 <2.0.0")
        assert not resolver._version_matches("2.0.0", ">=1.0.0 <2.0.0")

    def test_version_matches_wildcard(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        assert resolver._version_matches("1.0.0", "*")
        assert resolver._version_matches("99.0.0", "*")

    def test_add_constraint(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        resolver._add_constraint("@user/skill", "^1.0.0", "root")
        resolver._add_constraint("@user/skill", ">=1.5.0", "@other/skill")

        assert len(resolver._constraints["@user/skill"]) == 2
        assert ("root", "^1.0.0") in resolver._constraints["@user/skill"]
        assert ("@other/skill", ">=1.5.0") in resolver._constraints["@user/skill"]


class TestTopologicalSort:
    def test_simple_sort(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        resolver._resolved = {
            "a": ResolvedSkill(
                name="a",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=["b"],
            ),
            "b": ResolvedSkill(
                name="b",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=[],
            ),
        }

        result = resolver._topological_sort()
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"a", "b"}

    def test_complex_sort(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        resolver._resolved = {
            "a": ResolvedSkill(
                name="a",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=["b", "c"],
            ),
            "b": ResolvedSkill(
                name="b",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=["c"],
            ),
            "c": ResolvedSkill(
                name="c",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=[],
            ),
        }

        result = resolver._topological_sort()
        assert len(result) == 3
        names = {s.name for s in result}
        assert names == {"a", "b", "c"}

    def test_sort_with_independent_nodes(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        resolver._resolved = {
            "a": ResolvedSkill(
                name="a",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=[],
            ),
            "b": ResolvedSkill(
                name="b",
                version="1.0.0",
                registry=None,
                tarball_url=None,
                checksum=None,
                dependencies=[],
            ),
        }

        result = resolver._topological_sort()
        assert len(result) == 2


class TestParseDependencies:
    def test_parse_string_dependencies(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        data = {"capabilities": {"dependencies": ["@user/skill-a", "@user/skill-b"]}}

        deps = resolver._parse_dependencies(data)
        assert len(deps) == 2
        assert deps[0].name == "@user/skill-a"
        assert deps[0].version == "*"

    def test_parse_dict_dependencies(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        data = {
            "capabilities": {
                "dependencies": [{"name": "@user/skill", "version": "^1.0.0", "optional": True}]
            }
        }

        deps = resolver._parse_dependencies(data)
        assert len(deps) == 1
        assert deps[0].name == "@user/skill"
        assert deps[0].version == "^1.0.0"
        assert deps[0].optional is True

    def test_parse_empty_dependencies(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        data = {}

        deps = resolver._parse_dependencies(data)
        assert deps == []

    def test_parse_mixed_dependencies(self):
        resolver = DependencyResolver(
            registry_manager=None, lockfile_manager=None, use_lockfile=False
        )
        data = {
            "capabilities": {
                "dependencies": [
                    "@user/simple",
                    {"name": "@user/complex", "version": "~1.2.0"},
                ]
            }
        }

        deps = resolver._parse_dependencies(data)
        assert len(deps) == 2
        assert deps[0].name == "@user/simple"
        assert deps[1].version == "~1.2.0"

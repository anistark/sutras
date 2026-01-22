"""Dependency resolution for Sutras.

Provides dependency resolution with:
- Recursive dependency resolution
- Conflict detection
- Circular dependency detection
- Topological sorting for install order
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .abi import DependencyConfig
from .lockfile import LockfileManager
from .naming import SkillName
from .registry import RegistryManager, SkillIndexEntry
from .semver import Version, VersionRange


@dataclass
class ResolvedSkill:
    """A resolved skill with exact version."""

    name: str
    version: str
    registry: str | None
    tarball_url: str | None
    checksum: str | None
    dependencies: list[str] = field(default_factory=list)


class DependencyConflictError(Exception):
    """Raised when dependency versions conflict."""

    def __init__(self, skill_name: str, constraints: list[tuple[str, str]]):
        self.skill_name = skill_name
        self.constraints = constraints
        constraint_strs = [f"{src}: {c}" for src, c in constraints]
        super().__init__(
            f"Conflicting version constraints for '{skill_name}':\n  "
            + "\n  ".join(constraint_strs)
        )


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle + [cycle[0]])
        super().__init__(f"Circular dependency detected: {cycle_str}")


class SkillNotFoundError(Exception):
    """Raised when a skill cannot be found."""

    def __init__(self, skill_name: str, constraint: str | None = None):
        self.skill_name = skill_name
        self.constraint = constraint
        msg = f"Skill '{skill_name}' not found in any registry"
        if constraint:
            msg += f" (constraint: {constraint})"
        super().__init__(msg)


class NoMatchingVersionError(Exception):
    """Raised when no version matches the constraint."""

    def __init__(self, skill_name: str, constraint: str, available: list[str]):
        self.skill_name = skill_name
        self.constraint = constraint
        self.available = available
        super().__init__(
            f"No version of '{skill_name}' matches constraint '{constraint}'. "
            f"Available: {', '.join(available) if available else 'none'}"
        )


@dataclass
class DependencyRequest:
    """A request to resolve a dependency."""

    name: str
    constraint: str
    source: str
    registry: str | None = None
    optional: bool = False


class DependencyResolver:
    """Resolves skill dependencies with conflict detection."""

    def __init__(
        self,
        registry_manager: RegistryManager | None = None,
        lockfile_manager: LockfileManager | None = None,
        use_lockfile: bool = True,
    ):
        self.registry_manager = registry_manager or RegistryManager()
        self.lockfile_manager = lockfile_manager or LockfileManager()
        self.use_lockfile = use_lockfile

        self._resolved: dict[str, ResolvedSkill] = {}
        self._constraints: dict[str, list[tuple[str, str]]] = {}
        self._resolution_stack: list[str] = []

    def resolve(self, dependencies: list[DependencyRequest]) -> list[ResolvedSkill]:
        """Resolve a list of dependencies.

        Args:
            dependencies: List of dependency requests

        Returns:
            List of resolved skills in installation order

        Raises:
            DependencyConflictError: If version constraints conflict
            CircularDependencyError: If circular dependencies exist
            SkillNotFoundError: If a skill cannot be found
            NoMatchingVersionError: If no version matches constraints
        """
        self._resolved = {}
        self._constraints = {}
        self._resolution_stack = []

        for dep in dependencies:
            if dep.optional:
                try:
                    self._resolve_one(dep)
                except (SkillNotFoundError, NoMatchingVersionError):
                    continue
            else:
                self._resolve_one(dep)

        return self._topological_sort()

    def _resolve_one(self, request: DependencyRequest) -> ResolvedSkill | None:
        """Resolve a single dependency.

        Args:
            request: Dependency request

        Returns:
            Resolved skill or None if already resolved compatibly
        """
        skill_name = request.name
        constraint = request.constraint

        self._add_constraint(skill_name, constraint, request.source)

        if skill_name in self._resolved:
            resolved = self._resolved[skill_name]
            if self._version_matches(resolved.version, constraint):
                return None
            raise DependencyConflictError(skill_name, self._constraints.get(skill_name, []))

        if skill_name in self._resolution_stack:
            cycle_start = self._resolution_stack.index(skill_name)
            raise CircularDependencyError(self._resolution_stack[cycle_start:])

        locked_version = None
        if self.use_lockfile and self.lockfile_manager.exists():
            locked_version = self.lockfile_manager.get_locked_version(skill_name)

        self._resolution_stack.append(skill_name)

        try:
            registry_name, entry, version = self._find_version(
                skill_name, constraint, request.registry, locked_version
            )

            tarball_url = entry.tarball_url
            if version in entry.versions:
                tarball_url = entry.versions[version]

            deps = self._get_skill_dependencies(skill_name, version, registry_name)

            resolved = ResolvedSkill(
                name=skill_name,
                version=version,
                registry=registry_name,
                tarball_url=tarball_url,
                checksum=entry.checksum,
                dependencies=[d.name for d in deps],
            )
            self._resolved[skill_name] = resolved

            for dep in deps:
                dep_request = DependencyRequest(
                    name=dep.name,
                    constraint=dep.version,
                    source=skill_name,
                    registry=dep.registry,
                    optional=dep.optional,
                )
                if dep.optional:
                    try:
                        self._resolve_one(dep_request)
                    except (SkillNotFoundError, NoMatchingVersionError):
                        continue
                else:
                    self._resolve_one(dep_request)

            return resolved
        finally:
            self._resolution_stack.pop()

    def _add_constraint(self, skill_name: str, constraint: str, source: str) -> None:
        """Record a constraint for conflict reporting."""
        if skill_name not in self._constraints:
            self._constraints[skill_name] = []
        self._constraints[skill_name].append((source, constraint))

    def _version_matches(self, version: str, constraint: str) -> bool:
        """Check if a version matches a constraint."""
        try:
            v = Version.parse(version)
            c = VersionRange.parse(constraint)
            return c.matches(v)
        except ValueError:
            return version == constraint

    def _find_version(
        self,
        skill_name: str,
        constraint: str,
        registry_name: str | None,
        locked_version: str | None,
    ) -> tuple[str, SkillIndexEntry, str]:
        """Find a version matching the constraint.

        Returns:
            Tuple of (registry_name, entry, selected_version)
        """
        if locked_version and self._version_matches(locked_version, constraint):
            results = self.registry_manager.search_skill(skill_name)
            for reg_name, entry in results:
                if locked_version == entry.version or locked_version in entry.versions:
                    return reg_name, entry, locked_version

        if registry_name:
            registry = self.registry_manager.get_registry(registry_name)
            if skill_name not in registry.index.skills:
                raise SkillNotFoundError(skill_name, constraint)
            entry = registry.index.skills[skill_name]
            version = self._select_version(entry, constraint, skill_name)
            return registry_name, entry, version

        results = self.registry_manager.search_skill(skill_name)
        if not results:
            raise SkillNotFoundError(skill_name, constraint)

        for reg_name, entry in results:
            try:
                version = self._select_version(entry, constraint, skill_name)
                return reg_name, entry, version
            except NoMatchingVersionError:
                continue

        _, first_entry = results[0]
        available = [first_entry.version] + list(first_entry.versions.keys())
        raise NoMatchingVersionError(skill_name, constraint, list(set(available)))

    def _select_version(self, entry: SkillIndexEntry, constraint: str, skill_name: str) -> str:
        """Select the best version from an entry."""
        available = [entry.version] + list(entry.versions.keys())
        available = list(set(available))

        try:
            version_range = VersionRange.parse(constraint)
            parsed_versions = []
            for v in available:
                try:
                    parsed_versions.append(Version.parse(v))
                except ValueError:
                    continue

            selected = version_range.select_highest(parsed_versions)
            if selected:
                return str(selected)
        except ValueError:
            if constraint in available:
                return constraint

        raise NoMatchingVersionError(skill_name, constraint, available)

    def _get_skill_dependencies(
        self, skill_name: str, version: str, registry_name: str
    ) -> list[DependencyConfig]:
        """Get dependencies for a skill version."""
        try:
            registry = self.registry_manager.get_registry(registry_name)
            skill_dir = (
                registry.cache_path / "skills" / skill_name.replace("@", "").replace("/", "_")
            )
            sutras_yaml = skill_dir / "sutras.yaml"

            if not sutras_yaml.exists():
                parsed = SkillName.parse(skill_name)
                skill_dir = registry.cache_path / "skills" / parsed.name
                sutras_yaml = skill_dir / "sutras.yaml"

            if sutras_yaml.exists():
                with open(sutras_yaml) as f:
                    data = yaml.safe_load(f) or {}
                return self._parse_dependencies(data)
        except Exception:
            pass

        return []

    def _parse_dependencies(self, skill_data: dict) -> list[DependencyConfig]:
        """Parse dependencies from skill data."""
        capabilities = skill_data.get("capabilities", {})
        raw_deps = capabilities.get("dependencies", [])

        deps = []
        for dep in raw_deps:
            if isinstance(dep, str):
                deps.append(DependencyConfig(name=dep, version="*"))
            elif isinstance(dep, dict):
                deps.append(DependencyConfig(**dep))

        return deps

    def _topological_sort(self) -> list[ResolvedSkill]:
        """Sort resolved skills in dependency order (leaves first)."""
        in_degree: dict[str, int] = dict.fromkeys(self._resolved, 0)
        for skill in self._resolved.values():
            for dep in skill.dependencies:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            name = queue.pop(0)
            result.append(self._resolved[name])

            for dep in self._resolved[name].dependencies:
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        if len(result) != len(self._resolved):
            missing = set(self._resolved.keys()) - {s.name for s in result}
            raise CircularDependencyError(list(missing))

        return result

    def update_lockfile(self, resolved: list[ResolvedSkill]) -> None:
        """Update the lockfile with resolved dependencies.

        Args:
            resolved: List of resolved skills
        """
        from .lockfile import LockedSkill, Lockfile

        lockfile = Lockfile()
        for skill in resolved:
            lockfile.skills[skill.name] = LockedSkill(
                name=skill.name,
                version=skill.version,
                checksum=skill.checksum,
                registry=skill.registry,
                tarball_url=skill.tarball_url,
                dependencies=skill.dependencies,
            )

        self.lockfile_manager.save(lockfile)


def resolve_dependencies(
    dependencies: list[dict | str],
    registry_manager: RegistryManager | None = None,
    project_path: Path | None = None,
    use_lockfile: bool = True,
) -> list[ResolvedSkill]:
    """Convenience function to resolve dependencies.

    Args:
        dependencies: List of dependency specs (strings or dicts)
        registry_manager: Registry manager to use
        project_path: Project path for lockfile
        use_lockfile: Whether to respect existing lockfile

    Returns:
        List of resolved skills in installation order
    """
    lockfile_manager = LockfileManager(project_path) if project_path else LockfileManager()

    resolver = DependencyResolver(
        registry_manager=registry_manager,
        lockfile_manager=lockfile_manager,
        use_lockfile=use_lockfile,
    )

    requests = []
    for dep in dependencies:
        if isinstance(dep, str):
            requests.append(
                DependencyRequest(
                    name=dep,
                    constraint="*",
                    source="root",
                )
            )
        elif isinstance(dep, dict):
            requests.append(
                DependencyRequest(
                    name=dep.get("name", ""),
                    constraint=dep.get("version", "*"),
                    source="root",
                    registry=dep.get("registry"),
                    optional=dep.get("optional", False),
                )
            )

    return resolver.resolve(requests)

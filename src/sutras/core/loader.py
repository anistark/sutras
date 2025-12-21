"""Skill discovery and loading functionality."""

from pathlib import Path

from sutras.core.skill import Skill


class SkillLoader:
    """Loads skills from Anthropic Skills directories."""

    def __init__(
        self,
        search_paths: list[Path] | None = None,
        include_global: bool = True,
        include_project: bool = True,
    ):
        """
        Initialize the skill loader.

        Args:
            search_paths: Custom search paths (overrides default)
            include_global: Include global skills from ~/.claude/skills/
            include_project: Include project skills from .claude/skills/
        """
        if search_paths:
            self.search_paths = search_paths
        else:
            self.search_paths = []
            if include_project:
                self.search_paths.append(Path.cwd() / ".claude" / "skills")
            if include_global:
                global_skills = Path.home() / ".claude" / "skills"
                if global_skills.exists():
                    self.search_paths.append(global_skills)

        self._loaded_skills: dict[str, Skill] = {}

    @property
    def skills_dir(self) -> Path:
        """Get the primary skills directory (project if exists, else global)."""
        project_dir = Path.cwd() / ".claude" / "skills"
        if project_dir.exists():
            return project_dir
        return Path.home() / ".claude" / "skills"

    def discover(self) -> list[str]:
        """
        Discover available skills in search paths.

        Returns:
            List of skill names
        """
        discovered = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for item in search_path.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    discovered.add(item.name)

        return sorted(discovered)

    def load(self, name: str) -> Skill:
        """
        Load a skill by name.

        Args:
            name: Name of the skill to load

        Returns:
            The loaded skill

        Raises:
            FileNotFoundError: If the skill cannot be found
            ValueError: If the skill is malformed
        """
        # Check if already loaded
        if name in self._loaded_skills:
            return self._loaded_skills[name]

        # Search for the skill
        skill_path = None
        for search_path in self.search_paths:
            candidate = search_path / name
            if candidate.exists() and (candidate / "SKILL.md").exists():
                skill_path = candidate
                break

        if not skill_path:
            raise FileNotFoundError(
                f"Skill '{name}' not found in search paths: {self.search_paths}"
            )

        # Load the skill
        skill = Skill.load(skill_path)

        # Cache and return
        self._loaded_skills[name] = skill
        return skill

    def get(self, name: str) -> Skill | None:
        """
        Get a loaded skill by name.

        Args:
            name: Name of the skill

        Returns:
            The skill if loaded, None otherwise
        """
        return self._loaded_skills.get(name)

    def list_loaded(self) -> list[str]:
        """
        List all loaded skills.

        Returns:
            List of loaded skill names
        """
        return list(self._loaded_skills.keys())

    def search(self, query: str) -> list[Skill]:
        """
        Search for skills matching a query.

        Args:
            query: Search query (matches name, description, tags)

        Returns:
            List of matching skills
        """
        query_lower = query.lower()
        results = []

        for skill_name in self.discover():
            try:
                skill = self.load(skill_name)

                # Search in name
                if query_lower in skill.name.lower():
                    results.append(skill)
                    continue

                # Search in description
                if query_lower in skill.description.lower():
                    results.append(skill)
                    continue

                # Search in tags
                if skill.abi and skill.abi.distribution:
                    tags = skill.abi.distribution.tags
                    if any(query_lower in tag.lower() for tag in tags):
                        results.append(skill)
                        continue

            except (FileNotFoundError, ValueError):
                # Skip malformed skills
                continue

        return results

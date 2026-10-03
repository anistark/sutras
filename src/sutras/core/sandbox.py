"""Temporary workspaces for isolated bench runs."""

import difflib
import shutil
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path

from sutras.core.naming import SkillName
from sutras.core.skill import Skill

_ALWAYS_IGNORED = {".sutras", ".git", "__pycache__", ".DS_Store"}


def skill_install_name(skill: Skill) -> str:
    """Directory name the skill is installed under (bare part of a scoped name)."""
    try:
        return SkillName.parse(skill.name).name
    except ValueError:
        return skill.path.absolute().name


class Sandbox:
    """A throwaway project directory with the skill installed in ``.claude/skills/``.

    Use as a context manager; the directory is removed on exit unless ``keep``
    is set.
    """

    def __init__(
        self,
        skill: Skill,
        workspace: Path | None = None,
        keep: bool = False,
        exclude: Iterable[Path] = (),
    ):
        self.skill = skill
        self.workspace = workspace
        self.keep = keep
        self.exclude = {p.resolve() for p in exclude}
        self._tmp: Path | None = None
        self.root = Path()

    def __enter__(self) -> "Sandbox":
        self._tmp = Path(tempfile.mkdtemp(prefix="sutras-bench-"))
        self.root = self._tmp / "workspace"
        if self.workspace:
            shutil.copytree(self.workspace, self.root, symlinks=True, ignore=_ignore(set()))
        else:
            self.root.mkdir()

        skill_dest = self.root / ".claude" / "skills" / skill_install_name(self.skill)
        shutil.copytree(self.skill.path, skill_dest, symlinks=True, ignore=_ignore(self.exclude))
        return self

    def __exit__(self, *exc: object) -> None:
        if self._tmp and not self.keep:
            shutil.rmtree(self._tmp, ignore_errors=True)

    def resolve(self, relative: str) -> Path:
        """Resolve a workspace-relative path, refusing paths that escape the sandbox.

        Raises:
            ValueError: If the path points outside the workspace
        """
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Path '{relative}' is outside the workspace")
        return path

    def diff(self, limit: int = 20_000) -> str:
        """Unified diff of the workspace against the original, excluding ``.claude/``."""
        return workspace_diff(self.workspace, self.root, limit)


def _ignore(excluded: set[Path]) -> Callable[[str, list[str]], set[str]]:
    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {n for n in names if n in _ALWAYS_IGNORED}
        if excluded:
            base = Path(directory).resolve()
            ignored |= {n for n in names if (base / n) in excluded}
        return ignored

    return ignore


def _text_files(root: Path | None) -> dict[str, Path]:
    if root is None or not root.exists():
        return {}
    files = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and rel.parts[0] != ".claude" and not set(rel.parts) & _ALWAYS_IGNORED:
            files[rel.as_posix()] = path
    return files


def _read_lines(path: Path | None) -> list[str] | None:
    if path is None:
        return []
    try:
        return path.read_text().splitlines(keepends=True)
    except (UnicodeDecodeError, OSError):
        return None


def workspace_diff(original: Path | None, current: Path, limit: int = 20_000) -> str:
    """Unified diff between two workspace trees, truncated to ``limit`` characters."""
    before = _text_files(original)
    after = _text_files(current)
    chunks: list[str] = []

    for rel in sorted(before.keys() | after.keys()):
        old_lines = _read_lines(before.get(rel))
        new_lines = _read_lines(after.get(rel))
        if old_lines is None or new_lines is None:
            if (rel in before) != (rel in after):
                chunks.append(f"Binary file {rel} {'added' if rel in after else 'deleted'}\n")
            continue
        if old_lines == new_lines:
            continue
        chunks.extend(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel}" if rel in before else "/dev/null",
                tofile=f"b/{rel}" if rel in after else "/dev/null",
            )
        )

    text = "".join(chunks)
    if len(text) > limit:
        text = text[:limit] + f"\n... (diff truncated at {limit} characters)\n"
    return text

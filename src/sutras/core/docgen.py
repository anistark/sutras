"""Skill documentation generator.

Auto-generates markdown documentation from SKILL.md, sutras.yaml,
and supporting files.
"""

from pathlib import Path

from sutras.core.skill import Skill


def generate_docs(skill: Skill, include_supporting: bool = True) -> str:
    """Generate markdown documentation for a skill.

    Args:
        skill: Loaded Skill instance.
        include_supporting: Whether to include supporting file contents.

    Returns:
        Generated markdown string.
    """
    sections: list[str] = []

    title = skill.name.replace("-", " ").replace("_", " ").title()
    sections.append(f"# {title}")
    sections.append("")

    # Badge line
    badges: list[str] = []
    if skill.version:
        badges.append(f"**Version:** {skill.version}")
    if skill.author:
        badges.append(f"**Author:** {skill.author}")
    if skill.abi and skill.abi.license:
        badges.append(f"**License:** {skill.abi.license}")
    if badges:
        sections.append(" | ".join(badges))
        sections.append("")

    # Description
    if skill.description:
        sections.append(f"> {skill.description}")
        sections.append("")

    # Metadata table
    meta_rows = _build_metadata_rows(skill)
    if meta_rows:
        sections.append("## Metadata")
        sections.append("")
        sections.append("| Field | Value |")
        sections.append("|-------|-------|")
        for field, value in meta_rows:
            sections.append(f"| {field} | {value} |")
        sections.append("")

    # Tools
    tools = _collect_tools(skill)
    if tools:
        sections.append("## Tools")
        sections.append("")
        sections.append(", ".join(f"`{t}`" for t in tools))
        sections.append("")

    # Dependencies
    deps = _collect_dependencies(skill)
    if deps:
        sections.append("## Dependencies")
        sections.append("")
        for dep in deps:
            sections.append(f"- {dep}")
        sections.append("")

    # Instructions from SKILL.md body
    if skill.instructions:
        sections.append("## Instructions")
        sections.append("")
        sections.append(skill.instructions)
        sections.append("")

    # Test cases
    if skill.abi and skill.abi.tests and skill.abi.tests.cases:
        sections.append("## Tests")
        sections.append("")
        sections.append("| Name | Description |")
        sections.append("|------|-------------|")
        for case in skill.abi.tests.cases:
            desc = case.description or ""
            sections.append(f"| {case.name} | {desc} |")
        sections.append("")

    # Evaluation config
    if skill.abi and skill.abi.eval:
        ev = skill.abi.eval
        sections.append("## Evaluation")
        sections.append("")
        sections.append(f"- **Framework:** {ev.framework}")
        if ev.metrics:
            sections.append(f"- **Metrics:** {', '.join(ev.metrics)}")
        if ev.threshold is not None:
            sections.append(f"- **Threshold:** {ev.threshold}")
        if ev.dataset:
            sections.append(f"- **Dataset:** `{ev.dataset}`")
        sections.append("")

    # Supporting files
    if include_supporting and skill.supporting_files:
        for filename in sorted(skill.supporting_files.keys()):
            filepath = skill.supporting_files[filename]
            if not filepath.suffix == ".md":
                continue
            try:
                content = filepath.read_text().strip()
            except OSError:
                continue
            if content:
                sections.append("---")
                sections.append("")
                sections.append(content)
                sections.append("")

    return "\n".join(sections).rstrip() + "\n"


def write_docs(skill: Skill, output: Path, include_supporting: bool = True) -> Path:
    """Generate documentation and write to a file.

    Args:
        skill: Loaded Skill instance.
        output: Output file path or directory. If a directory, writes ``<name>.md``.
        include_supporting: Whether to include supporting file contents.

    Returns:
        Path to the written file.
    """
    content = generate_docs(skill, include_supporting=include_supporting)

    if output.is_dir():
        output = output / f"{skill.name}.md"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return output


def _build_metadata_rows(skill: Skill) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if skill.abi:
        if skill.abi.repository:
            rows.append(("Repository", skill.abi.repository))
        if skill.abi.distribution:
            dist = skill.abi.distribution
            if dist.category:
                rows.append(("Category", dist.category))
            if dist.tags:
                rows.append(("Tags", ", ".join(dist.tags)))
            if dist.keywords:
                rows.append(("Keywords", ", ".join(dist.keywords)))
            if dist.homepage:
                rows.append(("Homepage", dist.homepage))
            if dist.documentation:
                rows.append(("Documentation", dist.documentation))
    return rows


def _collect_tools(skill: Skill) -> list[str]:
    tools: list[str] = []
    if skill.allowed_tools:
        tools.extend(skill.allowed_tools)
    if skill.abi and skill.abi.capabilities and skill.abi.capabilities.tools:
        for t in skill.abi.capabilities.tools:
            if t not in tools:
                tools.append(t)
    return tools


def _collect_dependencies(skill: Skill) -> list[str]:
    if not skill.abi or not skill.abi.capabilities:
        return []
    deps = skill.abi.capabilities.dependencies
    if not deps:
        return []
    result: list[str] = []
    for dep in deps:
        if isinstance(dep, str):
            result.append(f"`{dep}`")
        else:
            version_str = f" ({dep.version})" if dep.version and dep.version != "*" else ""
            optional_str = " *(optional)*" if dep.optional else ""
            result.append(f"`{dep.name}`{version_str}{optional_str}")
    return result

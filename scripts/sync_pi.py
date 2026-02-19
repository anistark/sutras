"""Generate pi skill and extension from the sutras Click CLI.

Introspects the Click command tree to produce:
  - pi/skills/sutras/SKILL.md
  - pi/extensions/sutras.ts  (auto-generated sections only)
  - src/sutras/data/skills/sutras/SKILL.md  (bundled copy for `sutras setup`)

Usage:
  python scripts/sync_pi.py          # Generate files
  python scripts/sync_pi.py --check  # Exit 1 if files would change
"""

from __future__ import annotations

import difflib
import sys
import tomllib
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parent.parent
PI_SKILL_PATH = ROOT / "pi" / "skills" / "sutras" / "SKILL.md"
PI_EXT_PATH = ROOT / "pi" / "extensions" / "sutras.ts"
BUNDLED_SKILL_PATH = ROOT / "src" / "sutras" / "data" / "skills" / "sutras" / "SKILL.md"

AUTO_START = "// ── AUTO-GENERATED:START ──"
AUTO_END = "// ── AUTO-GENERATED:END ──"


def get_version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def get_cli_commands() -> list[dict]:
    from sutras.cli.main import cli

    commands = []
    for name, cmd in sorted(cli.commands.items()):
        if isinstance(cmd, click.Group):
            for sub_name, sub_cmd in sorted(cmd.commands.items()):
                commands.append({
                    "name": f"{name} {sub_name}",
                    "help": (sub_cmd.help or "").strip().split("\n")[0],
                    "params": _extract_params(sub_cmd),
                })
        else:
            commands.append({
                "name": name,
                "help": (cmd.help or "").strip().split("\n")[0],
                "params": _extract_params(cmd),
            })
    return commands


def _extract_params(cmd: click.Command) -> list[dict]:
    params = []
    for param in cmd.params:
        if isinstance(param, click.Argument):
            params.append({"name": param.name, "kind": "argument", "required": param.required})
        elif isinstance(param, click.Option):
            opts = "/".join(param.opts)
            params.append({
                "name": opts,
                "kind": "option",
                "help": (param.help or "").strip(),
                "is_flag": param.is_flag,
            })
    return params


# ── SKILL.md generation ──────────────────────────────────────────────────────


def generate_skill_md(commands: list[dict], version: str) -> str:
    cmd_ref_lines = []
    for cmd in commands:
        args = ""
        for p in cmd["params"]:
            if p["kind"] == "argument":
                args += f" <{p['name']}>" if p.get("required") else f" [{p['name']}]"
        cmd_ref_lines.append(f"sutras {cmd['name']}{args}")
        if cmd["help"]:
            cmd_ref_lines.append(f"    {cmd['help']}")
        opts = [p for p in cmd["params"] if p["kind"] == "option"]
        for opt in opts:
            flag_hint = " (flag)" if opt.get("is_flag") else ""
            cmd_ref_lines.append(f"    {opt['name']}{flag_hint}: {opt.get('help', '')}")
        cmd_ref_lines.append("")

    cmd_block = "\n".join(cmd_ref_lines).rstrip()

    return f"""\
---
name: sutras
description: >
  Create, validate, test, build, and distribute Anthropic Agent Skills using the Sutras CLI.
  Use when the user asks to create a new skill, scaffold skill structure, validate SKILL.md files,
  manage skill metadata, run skill tests/evaluations, build distributable packages, or publish
  skills to registries. Version {version}.
---

# Sutras — Skill Development Toolkit

Sutras is a CLI for the full lifecycle of Anthropic Agent Skills:
scaffolding, validation, testing, evaluation, packaging, and distribution.

## Command Reference

```
{cmd_block}
```

## SKILL.md Format

Every skill requires a `SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
description: >
  What it does and when the agent should use it.
  Be specific — the description drives skill discovery.
allowed-tools: Read, Write, Bash
---
```

Name rules: lowercase a-z, 0-9, hyphens only, max 64 chars.

## sutras.yaml Format

Extended metadata for lifecycle management:

```yaml
version: "1.0.0"
author: "Your Name"
license: "MIT"

capabilities:
  tools: [Read, Write, Bash]
  dependencies:
    - name: "@utils/common"
      version: "^1.0.0"

tests:
  cases:
    - name: "basic-test"
      inputs: {{example: "value"}}
      expected: {{status: "success"}}

eval:
  framework: "ragas"
  metrics: ["faithfulness", "answer_relevancy"]
  threshold: 0.7

distribution:
  tags: ["automation", "pdf"]
  category: "document-processing"
```

## Skill Locations

| Location | Scope | Command |
|----------|-------|---------|
| `.claude/skills/` | Project (shared via git) | `sutras new <name>` |
| `~/.claude/skills/` | Global (personal) | `sutras new <name> --global` |

For pi users, add to `.pi/settings.json`:
```json
{{"skills": [".claude/skills", "~/.claude/skills"]}}
```

## Best Practices

1. Write clear, specific descriptions — they drive agent skill discovery.
2. Add tests early in `sutras.yaml` to validate skill behavior.
3. Version your skills with semver for reproducible distribution.
4. Use templates (`--template code-review`, etc.) for best-practice structure.
5. Validate before sharing: `sutras validate --strict`.
6. Use scoped names for publishing: `@namespace/skill-name`.
"""


# ── Extension auto-generated block ───────────────────────────────────────────


def generate_extension_block(commands: list[dict]) -> str:
    entries = []
    for cmd in commands:
        entries.append(
            f'\t\t{{ value: "{cmd["name"]}", label: "{cmd["name"]} — {cmd["help"]}" }},'
        )

    subcommands_block = "\n".join(entries)

    return f"""\
const SUBCOMMANDS: {{ value: string; label: string }}[] = [
{subcommands_block}
\t];"""


# ── File writing with check mode ────────────────────────────────────────────


def write_or_check(path: Path, content: str, check: bool) -> bool:
    """Write content to path. In check mode, return True if content differs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text()
        if existing == content:
            return False
        if check:
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path) + " (generated)",
            )
            sys.stderr.writelines(diff)
            return True
    elif check:
        print(f"Missing: {path}", file=sys.stderr)
        return True

    path.write_text(content)
    print(f"  wrote {path.relative_to(ROOT)}")
    return False


def update_extension(ext_path: Path, block: str, check: bool) -> bool:
    """Update the auto-generated section of the extension file."""
    if not ext_path.exists():
        print(f"Warning: {ext_path} does not exist, skipping extension update", file=sys.stderr)
        return False

    content = ext_path.read_text()
    start = content.find(AUTO_START)
    end = content.find(AUTO_END)

    if start == -1 or end == -1:
        print(
            f"Warning: auto-generated markers not found in {ext_path}",
            file=sys.stderr,
        )
        return False

    new_content = content[: start + len(AUTO_START)] + "\n\t" + block + "\n\t" + content[end:]
    return write_or_check(ext_path, new_content, check)


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    check = "--check" in sys.argv

    version = get_version()
    commands = get_cli_commands()

    if check:
        print("Checking pi sync...")
    else:
        print(f"Syncing pi files (v{version}, {len(commands)} commands)...")

    skill_md = generate_skill_md(commands, version)
    ext_block = generate_extension_block(commands)

    changed = False
    changed |= write_or_check(PI_SKILL_PATH, skill_md, check)
    changed |= write_or_check(BUNDLED_SKILL_PATH, skill_md, check)
    changed |= update_extension(PI_EXT_PATH, ext_block, check)

    # Sync version to pi/package.json
    import json

    pkg_path = ROOT / "pi" / "package.json"
    pkg = json.loads(pkg_path.read_text())
    if pkg["version"] != version:
        pkg["version"] = version
        new_pkg = json.dumps(pkg, indent=2) + "\n"
        changed |= write_or_check(pkg_path, new_pkg, check)

    if check and changed:
        print("\npi files are out of sync. Run: just sync-pi", file=sys.stderr)
        sys.exit(1)
    elif not check:
        print("Done.")


if __name__ == "__main__":
    main()

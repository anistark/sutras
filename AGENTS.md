# AGENTS.md — AI Coding Agent Instructions for Sutras

> Instructions for Claude Code, Cursor, Copilot, pi, opencode and other AI coding agents working on this project.

---

## Project Overview

**Sutras** is the universal devtool for agent skills — create, test, evaluate, distribute, and discover skills for AI coding agents (Claude Code, Cursor, Windsurf, Copilot, and more).

- **Repository:** https://github.com/anistark/sutras
- **PyPI:** https://pypi.org/project/sutras/
- **Docs:** https://anistark.github.io/sutras/
- **License:** MIT
- **Python:** >=3.11
- **Build system:** hatchling (via `uv`)

---

## Architecture

Sutras is a Python CLI built with Click. It has two layers:

### 1. Core Library (`src/sutras/core/`)

The engine — models, loaders, runners, and managers. All business logic lives here.

| File | Purpose |
|------|---------|
| `abi.py` | Pydantic models for `sutras.yaml` (SutrasABI, TestConfig, EvalConfig, etc.) |
| `skill.py` | `Skill` model — combines SKILL.md frontmatter with ABI metadata |
| `loader.py` | `SkillLoader` — discovers and loads skills from `~/.claude/skills/` and `.claude/skills/` |
| `config.py` | `SutrasConfig` — global config from `~/.sutras/config.yaml`, registry entries |
| `templates.py` | Built-in skill templates for `sutras new --template` |
| `test_runner.py` | `TestRunner` — executes test cases defined in `sutras.yaml` |
| `evaluator.py` | `Evaluator` — Ragas-based evaluation framework |
| `builder.py` | `SkillBuilder` — packages skills into tarballs for distribution |
| `naming.py` | `SkillName` parser — handles `@namespace/skill` and bare names |
| `semver.py` | Semver constraint parsing (npm-style: `^1.0.0`, `~1.2.3`, ranges) |
| `registry.py` | `RegistryManager` — federated git-based registry system |
| `installer.py` | `SkillInstaller` — installs skills to `~/.claude/installed/` with symlinks |
| `publisher.py` | `SkillPublisher` — publishes skills to registries (direct push or PR) |
| `resolver.py` | `DependencyResolver` — recursive dependency resolution with conflict detection |
| `lockfile.py` | `.sutras.lock` format — lock file for reproducible installs |
| `docgen.py` | Documentation generation from skill metadata |
| `updater.py` | Self-update logic — checks PyPI, upgrades CLI, refreshes pi extension |

### 2. CLI Layer (`src/sutras/cli/main.py`)

A single `main.py` file with all Click commands. The CLI is the only entry point — there is no web UI or server.

**Commands:**

| Command | What it does |
|---------|-------------|
| `sutras list` | List discovered skills (local and global) |
| `sutras info <name>` | Show detailed skill information |
| `sutras new <name>` | Scaffold a new skill from a template |
| `sutras validate <name\|path>` | Validate skill structure and ABI; supports `--all` to validate every discovered skill (CI-friendly) and `--path <dir>` to override the skills directory |
| `sutras test <name>` | Run test cases from `sutras.yaml` |
| `sutras eval <name>` | Run evaluations (Ragas framework) |
| `sutras docs <name>` | Generate documentation from skill metadata |
| `sutras build <name>` | Package skill into distributable tarball |
| `sutras install <source>` | Install skill from registry, URL, GitHub, or local file |
| `sutras uninstall <name>` | Remove an installed skill |
| `sutras publish` | Publish skill to a registry |
| `sutras registry add/list/remove/update/build-index` | Manage federated registries |
| `sutras setup` | Install sutras as a Claude Code skill (symlink + pi extension) |
| `sutras update` | Self-update CLI and pi extension |

### 3. Pi Extension (`pi/`)

An npm package (`sutras`) that exposes sutras commands inside Claude Code (pi runtime). Contains auto-generated scripts and skills synced from CLI introspection via `scripts/sync_pi.py`.

### 4. Claude Plugin (`.claude-plugin/`)

Plugin metadata for Claude Code integration (`plugin.json`).

---

## Key Concepts

### Skill Structure

A skill is a directory containing:
```
my-skill/
  SKILL.md          # Required — Anthropic Skills format (YAML frontmatter + instructions)
  sutras.yaml       # Optional — Sutras ABI (version, tests, eval, distribution metadata)
  examples.md       # Optional — usage examples
  reference.md      # Optional — reference docs
```

**SKILL.md** must have YAML frontmatter with at minimum `name` and `description`:
```yaml
---
name: my-skill
description: What it does
allowed-tools: Read, Write, Bash
---

Instruction content here...
```

### Skill Locations

- **Project skills:** `.claude/skills/` (relative to cwd)
- **Global skills:** `~/.claude/skills/`
- **Installed skills:** `~/.claude/installed/<name>/<version>/` (symlinked into `~/.claude/skills/`)

### Federated Registry

Registries are git repos containing skill packages and an `index.yaml`. Users can add multiple registries (official, company, personal). Config lives in `~/.sutras/config.yaml`.

### Namespacing

- **Registry skills:** `@namespace/skill-name` (required for publishing)
- **Local skills:** `skill-name` (bare names, for local dev only)

---

## Development Setup

```bash
# Install dependencies
uv sync

# Run CLI from source
uv run sutras --help

# Or use just
just sutras list
```

### Quality Commands (via justfile)

| Command | What it does |
|---------|-------------|
| `just format` | Format with ruff |
| `just lint` | Lint with ruff |
| `just check` | Type check with ty |
| `just qa` | All three: format + lint + check |
| `just test` | Run pytest |
| `just test-cov` | Run pytest with coverage |
| `just pre-commit` | Full pre-commit checks (qa + test + sync check) |

### Publishing (For Maintainers only)

| Command | What it does |
|---------|-------------|
| `just publish` | Publish to PyPI + npm |
| `just publish-pypi` | PyPI only |
| `just publish-npm` | npm only (pi extension) |
| `just publish-test` | Test PyPI + npm dry run |
| `just check-versions` | Verify pyproject.toml and pi/package.json versions match |
| `just sync-pi` | Regenerate pi extension from CLI introspection |

---

## Agent Rules

- **No over-commenting.** Only add useful comments: detailed docstrings, `NOTE:` and `TODO:` annotations. Don't add inline comments restating what the code does.
- **Don't commit unless explicitly asked.** Never auto-commit.
- **Commit message style:** When asked to commit, review all changes and write the message in semver changelog style — brief, overview-level bullet points of what changed. No co-authored-by lines.
- **New CLI commands need examples.** If you add a new command, include a usage example in the help text and in this AGENTS.md under the CLI commands table.
- **Check `plan/` for existing plans.** Before starting work, check files under `plan/` for roadmaps, design docs, and task lists that may provide context or constraints for the task at hand.
- **Update the plan when completing plan tasks.** After finishing any task that originates from `plan/`, mark it as done (`[x]`) in the relevant plan file before moving on. The roadmap may be split across multiple documents.
- **Update CHANGELOG.md** when a relevant feature or bug fix is done. Follow the existing format in the file — group entries under the appropriate version heading. Keep it brief and follow SEMVER guidelines and existing formatting.

---

## Coding Conventions

### Style

- **Formatter/Linter:** ruff (line-length 100, target Python 3.11)
- **Type checker:** ty (Astral's Rust-based type checker)
- **Models:** Pydantic v2 `BaseModel` for data schemas, `@dataclass` for internal state
- **CLI:** Click with `@cli.command()` decorators — all commands in one file (`cli/main.py`)
- **Imports:** Use absolute imports from `sutras.core.*`
- **Quote style:** Double quotes
- **Indent:** 4 spaces

### Testing

- **Framework:** pytest
- **Location:** `tests/` at project root
- **Naming:** `test_<module>.py`, functions `test_<thing>()`
- **Run:** `just test` or `uv run python -m pytest`
- **Coverage:** `just test-cov`

### Version Management

- Version lives in `pyproject.toml` (`version = "X.Y.Z"`)
- Must match `pi/package.json` version — check with `just check-versions`
- Must match `.claude-plugin/plugin.json` version
- Semantic versioning (semver)

---

## Common Tasks for Agents

### Adding a new CLI command

1. Add the command function in `src/sutras/cli/main.py` with `@cli.command()` decorator
2. Follow existing patterns — use Click options/arguments, `click.echo()` for output, `click.style()` for colors
3. If it needs new core logic, add a module in `src/sutras/core/`
4. Export any new public classes from `src/sutras/__init__.py`
5. Add tests in `tests/test_<feature>.py`

### Adding a new ABI field

1. Add the Pydantic field to the appropriate model in `src/sutras/core/abi.py`
2. Update any CLI commands that display or use the field
3. Update templates in `src/sutras/core/templates.py` if it should appear in scaffolded skills
4. Add test cases

### Adding a new skill template

1. Create a `_<name>_template()` function in `src/sutras/core/templates.py`
2. Register it in the `_register_built_ins()` function
3. Follow the existing pattern: define `skill_md`, `sutras_yaml`, `examples_md` with `{name}`, `{description}`, `{author}`, `{title}` placeholders

### Modifying the installer/registry

1. Core logic is in `src/sutras/core/installer.py`, `registry.py`, `publisher.py`
2. Config schema is in `src/sutras/core/config.py`
3. Naming/version parsing in `naming.py` and `semver.py`
4. The installer uses symlinks: `~/.claude/skills/<name>` -> `~/.claude/installed/<name>/<version>/`

### Running sync after CLI changes

If you modify CLI commands, arguments, or help text, run:
```bash
just sync-pi
```
This regenerates the pi extension files from CLI introspection. Check with `just check-sync`.

---

## Important Paths

| Path | What it is |
|------|-----------|
| `pyproject.toml` | Project metadata, dependencies, tool config |
| `justfile` | All dev commands |
| `src/sutras/__init__.py` | Public API exports and version |
| `src/sutras/cli/main.py` | All CLI commands (single file) |
| `src/sutras/core/abi.py` | ABI schema definitions |
| `src/sutras/core/skill.py` | Skill model |
| `src/sutras/core/loader.py` | Skill discovery and loading |
| `src/sutras/core/config.py` | Global config (~/.sutras/config.yaml) |
| `src/sutras/core/templates.py` | Built-in skill templates |
| `pi/` | npm package for Claude Code pi extension |
| `scripts/sync_pi.py` | Syncs pi extension from CLI introspection |
| `.claude-plugin/plugin.json` | Claude Code plugin metadata |
| `plan/plan.md` | Development roadmap |
| `CHANGELOG.md` | Release history |
| `CONTRIBUTING.md` | Contribution guide |

---

## Gotchas & Pitfalls

- **All CLI commands are in one file.** `src/sutras/cli/main.py` is large by design — don't split it into separate modules unless explicitly asked.
- **`plan/` is gitignored.** It contains internal planning docs that are not shipped.
- **`.claude/` is gitignored.** It's the local skills directory created by `sutras new` and `sutras setup`. Don't commit it.
- **Three versions must stay in sync:** `pyproject.toml`, `pi/package.json`, and `.claude-plugin/plugin.json`. Use `just check-versions` to verify.
- **`ability.yaml` is legacy.** The codebase still supports it for backward compatibility, but `sutras.yaml` is the canonical name.
- **ruff lint ignores B904.** Within except clauses, `raise from` is not required — this is intentional for CLI abort patterns.
- **Optional dependency: `ragas`.** The eval command requires `pip install sutras[eval]`. Don't add ragas to core dependencies.
- **Optional dependency: sphinx.** Docs build requires `pip install sutras[docs]`.
- **Hardcoded `~/.claude/` paths.** The loader, installer, and config currently hardcode `~/.claude/` as the skills directory. This will change in v0.5 (runtime adapter system). For now, don't refactor these paths unless working on that feature.
- **Registry is git-based.** Registries are cloned/pulled as git repos into `~/.sutras/registry-cache/`. No HTTP API — everything goes through git.

---

## Examples

The `examples/` directory contains sample skills:
- `examples/skills/hello-claude/` — Minimal example skill

The `skills/sutras/` directory contains the `sutras` skill itself — a self-referential skill that provides sutras commands within Claude Code.

---

## Testing a Change End-to-End

```bash
# 1. Make your changes

# 2. Run quality checks
just qa

# 3. Run tests
just test

# 4. Test CLI manually
just sutras list
just sutras new test-skill
just sutras validate test-skill
just sutras info test-skill

# 5. Sync pi extension if CLI changed
just sync-pi

# 6. Verify versions
just check-versions
```

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/anistark/sutras/compare/v0.4.1...HEAD)

...

## [v0.4.1](https://github.com/anistark/sutras/compare/v0.4.0...v0.4.1) - 2026-02-21

### Added
- `/sutras help` command in pi extension — shows all available commands; `/sutras help <command>` shows detailed usage
- `postinstall.sh` script for automatic `sutras` CLI installation when pi package is installed via npm/git (tries `pipx` → `uv` → `pip` in order)
- Prerequisites section in SKILL.md — instructs the agent to check for `sutras` CLI availability and prompt the user to install if missing

### Changed
- Updated install hint messages in pi extension to recommend `pipx` / `uv` over bare `pip`
- SKILL.md description now declares minimum supported version (`>= 0.4.1`) instead of hardcoded version number

## [v0.4.0](https://github.com/anistark/sutras/compare/v0.3.0...v0.4.0)

### Added
- `sutras setup` command to install the sutras skill into Claude Code (`~/.claude/skills/sutras/`)
- Pi extension with `/sutras` command, autocomplete, interactive skill creation, and auto-validation on write
- Pi skill (SKILL.md) with full command reference for LLM-driven skill development
- npm package (`sutras` on npm) for `pi install npm:sutras`
- `scripts/sync_pi.py` to auto-generate pi skill + extension from Click CLI introspection
- `just sync-pi` and `just check-sync` recipes for sync enforcement

## [v0.3.0](https://github.com/anistark/sutras/compare/v0.2.0...v0.3.0) - 2026-02-08

### Added
- **Skill documentation generation**: `sutras docs` command to auto-generate Markdown reference from SKILL.md, sutras.yaml, and supporting files
  - Print to stdout or write to file/directory (`-o`)
  - Renders title, badges (version/author/license), metadata table, tools, dependencies, instructions, tests, evaluation config
  - Appends supporting `.md` file contents (e.g. examples.md); toggle with `--no-supporting`
  - Core library API: `generate_docs()` and `write_docs()` for programmatic use
- Skill documentation generation tests (`test_docgen.py`)
- CLI reference page for `sutras docs` (`docs/cli/docs.md`)
- **Skill templates**: `sutras new --template` for scaffolding skills from built-in templates
  - `default` - Minimal skill scaffold (existing behaviour, now explicit)
  - `code-review` - Code review skill with diff analysis and feedback patterns
  - `api-integration` - API integration skill with request handling and error patterns
  - `data-analysis` - Data analysis skill with file processing and reporting patterns
  - `automation` - Workflow automation skill with task orchestration patterns
  - `sutras new --list-templates` to discover available templates
- Skill template unit tests (`test_templates.py`)
- Templates guide (`docs/guides/templates.md`)
- Sphinx documentation with GitHub Pages deployment
- Documentation deploy workflow for automated publishing
- **Documentation guides**:
  - Registry usage guide (`docs/guides/registry.md`)
  - Publishing guide (`docs/guides/publishing.md`)
  - Private registry setup guide (`docs/guides/private-registry.md`)
- **Unit tests for core modules**:
  - Skill naming system tests (`test_naming.py`)
  - Semver constraint parsing tests (`test_semver.py`)
  - Configuration management tests (`test_config.py`)
  - Dependency resolver tests (`test_resolver.py`)

## [0.2.0](https://github.com/anistark/sutras/compare/v0.1.2...v0.2.0) - 2026-01-26

### Added
- Skill packaging system with `sutras build` command
- Semver validation for skill versions
- Tarball distribution support for packaged skills
- **Registry system**:
  - Federated Git-based registry infrastructure
  - Configuration management in `~/.sutras/config.yaml`
  - Skill naming system with namespace support (`@namespace/skill-name`)
  - `sutras registry` commands for managing registries:
    - `registry add` - Add new registry
    - `registry list` - List configured registries
    - `registry remove` - Remove registry
    - `registry update` - Update cached indexes
    - `registry build-index` - Generate index.yaml for local registry
  - `sutras install` command for installing skills from multiple sources:
    - Install from registries: `@namespace/skill-name`
    - Install from GitHub releases: `github:user/repo@version`
    - Install from direct URLs: `https://example.com/skill.tar.gz`
    - Install from local files: `./skill.tar.gz`
  - `sutras uninstall` command for removing installed skills
  - `sutras publish` command for publishing skills to registries
  - Support for multiple registries with priority ordering
  - Git-based registry caching in `~/.sutras/registry-cache/`
  - Installation to `~/.claude/installed/` with symlinks in `~/.claude/skills/`
  - SHA256 checksum verification for downloads
  - Pull request workflow support for public registries (`--pr` flag)
  - Private registry support via Git authentication
- **Dependency resolution system**:
  - Semver constraint parsing with npm-style syntax (`^1.0.0`, `~1.2.3`, `>=1.0.0 <2.0.0`, wildcards)
  - `DependencyConfig` model for declaring skill dependencies in `sutras.yaml`
  - Lock file support (`.sutras.lock`) for reproducible installations
  - `DependencyResolver` for recursive dependency resolution
  - Conflict detection for incompatible version constraints
  - Circular dependency detection
  - Topological sorting for correct installation order

### Changed
- **[Ragas](https://github.com/vibrantlabsai/ragas) evaluator migrated to v0.4 API**:
  - Import from `ragas.metrics.collections` instead of `ragas.metrics`
  - Use class-based metrics (`Faithfulness`, `AnswerRelevancy`, `ContextPrecision`)
  - Use `llm_factory()` and `embedding_factory()` for component initialization
  - Use async `metric.ascore()` method with `MetricResult` return type
  - Updated minimum ragas version to 0.4.3

## [0.1.2](https://github.com/anistark/sutras/compare/v0.1.1...v0.1.2) - 2026-01-01

### Added
- Ragas evaluation support for skill testing
- Optional `eval` dependencies for evaluation capabilities

## [0.1.1](https://github.com/anistark/sutras/compare/v0.1.0...v0.1.1) - 2025-12-29

### Added
- Testing framework with test runner
- Fixture management for skill tests
- `sutras test` command for running skill tests
- Architecture diagram documentation

### Changed
- Updated README with badges for PyPI version, downloads, and status

## [0.1.0](https://github.com/anistark/sutras/releases/tag/v0.1.0) - 2025-12-27

### Added
- Initial release of Sutras
- `sutras new` command for scaffolding new skills
- `sutras list` command for listing available skills
- `sutras info` command for viewing skill details
- `sutras validate` command with optional strict mode
- Support for local and global skill locations
- SKILL.md format with YAML frontmatter
- sutras.yaml metadata management
- Skill discovery and loading library
- CLI interface with Click framework
- Pydantic models for skill validation
- YAML parsing with PyYAML
- Jinja2 templating for skill generation

### Fixed
- CLI command execution issues
- Token usage tracking for uv publish

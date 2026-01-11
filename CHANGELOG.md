# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/anistark/sutras/compare/v0.1.2...HEAD)

### Added
- Skill packaging system with `sutras build` command
- Semver validation for skill versions
- Tarball distribution support for packaged skills

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

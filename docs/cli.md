# CLI Reference

## Skill Development

```sh
# Create a new skill
sutras new <name> [--description TEXT] [--author TEXT] [--global]

# List skills
sutras list [--local/--no-local] [--global/--no-global]

# Show skill details
sutras info <name>

# Validate skill
sutras validate <name> [--strict]

# Run tests
sutras test <name> [--verbose] [--fail-fast]

# Evaluate with metrics
sutras eval <name> [--verbose] [--no-history] [--show-history]
```

## Distribution

```sh
# Build distributable package
sutras build <name> [--output PATH] [--no-validate]

# Publish to registry
sutras publish [PATH] [--registry NAME] [--pr]

# Install from various sources
sutras install <SOURCE> [--version VERSION] [--registry NAME]
# SOURCE can be:
#   @namespace/skill-name           - From registry
#   github:user/repo@version        - From GitHub release
#   https://example.com/skill.tar.gz - From URL
#   ./skill.tar.gz                  - From local file

# Uninstall skill
sutras uninstall <skill-name> [--version VERSION]
```

## Registry Management

```sh
# Add a registry
sutras registry add <name> <git-url> [--namespace NS] [--priority N] [--default]

# List registries
sutras registry list

# Remove registry
sutras registry remove <name>

# Update registry index
sutras registry update <name>
sutras registry update --all

# Build index for local registry
sutras registry build-index <path> [--output PATH]
```

## Package and Distribute

### Building Packages

```sh
# Build a distributable package
sutras build my-skill

# Build with custom output directory
sutras build my-skill --output ./packages

# Skip validation
sutras build my-skill --no-validate
```

Creates a versioned tarball (e.g., `my-skill-1.0.0.tar.gz`) in `dist/` containing:
- SKILL.md and sutras.yaml
- Supporting files (examples.md, etc.)
- MANIFEST.json with checksums and metadata

**Requirements for distribution:**
- Version (semver format) in sutras.yaml
- Author in sutras.yaml
- License in sutras.yaml
- Valid skill name and description
- Scoped name format: `@namespace/skill-name` (required for registry publishing)

### Publishing to Registry

```sh
# Publish to default registry
sutras publish

# Publish to specific registry
sutras publish --registry my-registry

# Use pull request workflow (for public registries)
sutras publish --pr
```

**Publishing requirements:**
- All build requirements above
- Skill name must be scoped: `@username/skill-name`
- Registry must be configured with write access (or use --pr flag)

### Installing Skills

Skills can be installed from multiple sources:

**From Registry:**

```sh
# Install latest version from any configured registry
sutras install @username/skill-name

# Install specific version
sutras install @username/skill-name --version 1.2.0

# Install from specific registry
sutras install @username/skill-name --registry company-registry
```

**From GitHub Releases:**

```sh
# Install latest release
sutras install github:username/repo

# Install specific version
sutras install github:username/repo@v1.0.0
sutras install github:username/repo@1.0.0
```

**From Direct URL:**

```sh
# Install from any HTTPS URL
sutras install https://example.com/skills/my-skill-1.0.0.tar.gz
sutras install https://github.com/user/repo/releases/download/v1.0.0/skill.tar.gz
```

**From Local File:**

```sh
# Install from local tarball
sutras install ./dist/my-skill-1.0.0.tar.gz
sutras install /path/to/skill.tar.gz
```

Installed skills are placed in:
- `~/.claude/installed/` - Versioned skill installations
- `~/.claude/skills/` - Symlinks to active versions

### Registry Setup

```sh
# Add the official registry (example)
sutras registry add official https://github.com/anthropics/sutras-registry --default

# Add a company registry
sutras registry add company https://github.com/mycompany/skills-registry --priority 10

# Add a personal registry
sutras registry add personal https://github.com/myuser/my-skills

# Update all registry indexes
sutras registry update --all
```

**Registry features:**
- Federated Git-based design (like Homebrew taps, Go modules)
- No central infrastructure required
- Private registries via Git authentication
- Works offline with cached indexes
- Multiple registry support with priority ordering

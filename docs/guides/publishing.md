# Publishing Skills

This guide covers packaging and publishing skills to registries.

## Prerequisites

Before publishing, your skill needs:

1. **Scoped name** in SKILL.md: `@namespace/skill-name`
2. **Version** in sutras.yaml (semver format)
3. **Author** in sutras.yaml
4. **License** in sutras.yaml

## Preparing Your Skill

### Update SKILL.md

```yaml
---
name: "@username/my-skill"
description: A clear description of what this skill does
allowed-tools: Read, Write
---

# My Skill

Instructions for Claude...
```

### Update sutras.yaml

```yaml
version: "1.0.0"
author: "Your Name <your@email.com>"
license: "MIT"

capabilities:
  tools: [Read, Write]
  dependencies:
    - name: "@utils/helper"
      version: "^1.0.0"

distribution:
  tags: ["productivity", "automation"]
  category: "development"
```

### Validate

```sh
sutras validate @username/my-skill --strict
```

Fix any errors before proceeding.

## Building a Package

```sh
# Build to dist/ directory
sutras build @username/my-skill

# Build to custom location
sutras build @username/my-skill --output ./packages
```

This creates a tarball like `my-skill-1.0.0.tar.gz` containing:

```
my-skill-1.0.0/
├── SKILL.md
├── sutras.yaml
├── examples.md
└── MANIFEST.json
```

## Publishing Methods

### Direct to Registry

If you have write access to the registry:

```sh
# To default registry
sutras publish

# To specific registry
sutras publish --registry company
```

This pushes directly to the registry's Git repository.

### Pull Request Workflow

For public registries or when you don't have write access:

```sh
sutras publish --pr
```

This:
1. Forks the registry (if needed)
2. Creates a branch with your skill
3. Opens a pull request for review

### Manual Publishing

You can also publish manually:

1. Build your package: `sutras build @username/my-skill`
2. Copy the tarball to the registry's releases directory
3. Update `index.yaml` with your skill entry
4. Commit and push (or open a PR)

## Publishing to GitHub Releases

You can distribute skills without a registry using GitHub releases:

1. Build your package:
   ```sh
   sutras build @username/my-skill
   ```

2. Create a GitHub release and attach the `.tar.gz` file

3. Others can install directly:
   ```sh
   sutras install github:username/my-skill-repo@v1.0.0
   ```

## Version Management

### Incrementing Versions

Follow semantic versioning:

- **Major** (2.0.0): Breaking changes
- **Minor** (1.1.0): New features, backward compatible
- **Patch** (1.0.1): Bug fixes

Update `sutras.yaml` before each release:

```yaml
version: "1.1.0"  # was "1.0.0"
```

### Pre-release Versions

```yaml
version: "2.0.0-alpha.1"
version: "2.0.0-beta.2"
version: "2.0.0-rc.1"
```

## Declaring Dependencies

If your skill depends on others:

```yaml
capabilities:
  dependencies:
    # Simple dependency
    - "@utils/common"

    # With version constraint
    - name: "@tools/formatter"
      version: "^2.0.0"

    # From specific registry
    - name: "@company/internal-tool"
      version: ">=1.0.0"
      registry: "company"

    # Optional dependency
    - name: "@extra/nice-to-have"
      version: "*"
      optional: true
```

## Publishing Checklist

1. [ ] Skill has scoped name (`@namespace/skill-name`)
2. [ ] Version follows semver
3. [ ] Author and license specified
4. [ ] `sutras validate --strict` passes
5. [ ] Skill tested locally
6. [ ] CHANGELOG updated (if applicable)
7. [ ] Built successfully with `sutras build`
8. [ ] Tested installation from tarball

## Updating Published Skills

To publish a new version:

1. Update version in `sutras.yaml`
2. Build: `sutras build @username/my-skill`
3. Publish: `sutras publish`

The registry keeps previous versions available.

## Troubleshooting

### "Skill name must be scoped"

Change your skill name from `my-skill` to `@username/my-skill` in SKILL.md.

### "Missing required field"

Check `sutras.yaml` has:
- `version`
- `author`
- `license`

### "Registry not configured"

Add a registry first:
```sh
sutras registry add official https://github.com/anthropics/sutras-registry --default
```

### "Permission denied"

- For direct push: Verify you have write access
- Use `--pr` flag to submit via pull request
- Check Git credentials for private registries

## Next Steps

- [Private Registry Setup](private-registry.md) - Host your own registry
- [Registry Guide](registry.md) - Learn about the registry system

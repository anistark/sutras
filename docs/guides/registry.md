# Registry System

Sutras uses a federated Git-based registry system for skill distribution. This guide covers how registries work and how to use them.

## Overview

The registry system provides:

- **Decentralized Distribution** - Registries are Git repositories, no central server
- **Multiple Sources** - Use official, company, and personal registries together
- **Offline Support** - Cached indexes work without network access
- **Git Authentication** - Private registries use existing Git credentials

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Machine                             │
│                                                             │
│  ~/.sutras/                                                 │
│  ├── config.yaml          # Registry configuration          │
│  └── registry-cache/      # Cached registry indexes         │
│      ├── official/                                          │
│      └── company/                                           │
│                                                             │
│  ~/.claude/                                                 │
│  ├── installed/           # Versioned skill installations   │
│  │   └── user_skillname/                                   │
│  │       └── 1.0.0/                                        │
│  └── skills/              # Symlinks to active versions     │
│      └── skillname -> ../installed/user_skillname/1.0.0   │
└─────────────────────────────────────────────────────────────┘
```

## Setting Up Registries

### Add a Registry

```sh
# Add with basic options
sutras registry add official https://github.com/anthropics/sutras-registry

# Add with options
sutras registry add company https://github.com/mycompany/skills-registry \
    --priority 10 \
    --namespace mycompany \
    --default
```

**Options:**

| Option | Description |
|--------|-------------|
| `--priority N` | Search order (higher = checked first) |
| `--namespace NS` | Default namespace for this registry |
| `--default` | Set as default for publishing |

### List Registries

```sh
sutras registry list
```

Shows all configured registries with their URLs, priorities, and status.

### Update Registry Indexes

```sh
# Update one registry
sutras registry update official

# Update all registries
sutras registry update --all
```

This pulls the latest index from the remote Git repository.

### Remove a Registry

```sh
sutras registry remove old-registry
```

## Installing Skills

### From Registry

```sh
# Install latest version
sutras install @username/skill-name

# Install specific version
sutras install @username/skill-name --version 1.2.0

# Install from specific registry
sutras install @username/skill-name --registry company
```

### From GitHub Releases

```sh
# Latest release
sutras install github:user/repo

# Specific version
sutras install github:user/repo@v1.0.0
```

### From URL or File

```sh
# Direct URL
sutras install https://example.com/skills/my-skill-1.0.0.tar.gz

# Local file
sutras install ./dist/my-skill-1.0.0.tar.gz
```

## Skill Naming

Registry skills use scoped names: `@namespace/skill-name`

- **namespace** - Usually your username or organization
- **skill-name** - The skill identifier

Examples:
- `@anthropic/code-review`
- `@mycompany/deploy-helper`
- `@username/my-awesome-skill`

Local skills (development only) can use bare names like `my-skill`.

## Version Constraints

When declaring dependencies, use npm-style constraints:

| Constraint | Matches |
|------------|---------|
| `1.0.0` | Exactly 1.0.0 |
| `^1.0.0` | >=1.0.0 <2.0.0 |
| `~1.2.3` | >=1.2.3 <1.3.0 |
| `>=1.0.0 <2.0.0` | Explicit range |
| `1.x` or `1.*` | Any 1.x version |
| `*` | Any version |

## Lock Files

When you install skills with dependencies, Sutras creates `.sutras.lock`:

```yaml
version: 1
skills:
  "@user/main-skill":
    version: "1.0.0"
    checksum: "abc123..."
    registry: "official"
    dependencies:
      - "@utils/helper"
  "@utils/helper":
    version: "2.1.0"
    checksum: "def456..."
    registry: "official"
```

**Best practices:**
- Commit `.sutras.lock` to version control
- Run `sutras install` to restore exact versions
- Delete the lock file to get fresh resolutions

## Registry Index Format

Each registry has an `index.yaml` at its root:

```yaml
skills:
  "@namespace/skill-name":
    version: "1.0.0"
    description: "What this skill does"
    tarball_url: "releases/skill-name-1.0.0.tar.gz"
    checksum: "sha256:abc123..."
    versions:
      "1.0.0": "releases/skill-name-1.0.0.tar.gz"
      "0.9.0": "releases/skill-name-0.9.0.tar.gz"
```

Build the index automatically:

```sh
sutras registry build-index ./my-registry
```

## Troubleshooting

### "Skill not found"

1. Update registry indexes: `sutras registry update --all`
2. Check skill name spelling (case-sensitive)
3. Verify the registry contains the skill

### "No matching version"

1. Check available versions: `sutras info @user/skill`
2. Loosen your version constraint
3. Update the registry index

### "Authentication failed"

For private registries:
1. Ensure Git credentials are configured
2. Try cloning the repo manually to test access
3. Check SSH keys or HTTPS tokens

## Next Steps

- [Publishing Guide](publishing.md) - Share your skills
- [Private Registry Setup](private-registry.md) - Host your own registry

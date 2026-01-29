# Private Registry Setup

Run your own registry for internal skills distribution.

## Overview

A Sutras registry is a Git repository with a specific structure. You can host it on:

- GitHub (public or private)
- GitLab
- Bitbucket
- Self-hosted Git server
- Any Git hosting with HTTPS or SSH access

## Creating a Registry

### 1. Create the Repository

```sh
mkdir my-skills-registry
cd my-skills-registry
git init
```

### 2. Add Registry Metadata

Create `registry.yaml`:

```yaml
name: "My Skills Registry"
description: "Internal skills for our team"
maintainer: "team@example.com"
visibility: private
```

### 3. Create Directory Structure

```
my-skills-registry/
├── registry.yaml
├── index.yaml
├── skills/
│   └── @namespace/
│       └── skill-name/
│           ├── SKILL.md
│           └── sutras.yaml
└── releases/
    └── skill-name-1.0.0.tar.gz
```

### 4. Initialize the Index

Create an empty `index.yaml`:

```yaml
skills: {}
```

Or let Sutras build it:

```sh
sutras registry build-index .
```

### 5. Push to Remote

```sh
git add .
git commit -m "Initialize registry"
git remote add origin git@github.com:company/skills-registry.git
git push -u origin main
```

## Adding Skills to Your Registry

### Manual Method

1. Build the skill package:
   ```sh
   sutras build @mycompany/my-skill
   ```

2. Copy to registry:
   ```sh
   cp dist/my-skill-1.0.0.tar.gz /path/to/registry/releases/
   ```

3. Rebuild index:
   ```sh
   cd /path/to/registry
   sutras registry build-index .
   ```

4. Commit and push:
   ```sh
   git add .
   git commit -m "Add @mycompany/my-skill 1.0.0"
   git push
   ```

### Using Publish Command

If you have write access:

```sh
sutras publish --registry company
```

## Team Setup

### Add Registry for Team Members

Each team member adds the registry once:

```sh
sutras registry add company git@github.com:mycompany/skills-registry.git \
    --priority 10 \
    --default
```

### Installing from Private Registry

```sh
# Works just like public registries
sutras install @mycompany/internal-skill
```

## Authentication

### SSH Keys (Recommended)

If using SSH URLs (`git@github.com:...`):

1. Generate SSH key if needed:
   ```sh
   ssh-keygen -t ed25519 -C "your@email.com"
   ```

2. Add public key to your Git host

3. Use SSH URL when adding registry:
   ```sh
   sutras registry add company git@github.com:company/registry.git
   ```

### HTTPS with Tokens

For HTTPS URLs with token auth:

1. Create a personal access token on your Git host
2. Configure Git credential helper:
   ```sh
   git config --global credential.helper store
   ```
3. First Git operation will prompt for credentials

### GitHub App Token

For CI/CD environments, use GitHub App tokens or deploy keys.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Publish Skill

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Sutras
        run: pip install sutras

      - name: Configure Registry
        run: |
          sutras registry add company ${{ secrets.REGISTRY_URL }}

      - name: Build and Publish
        run: |
          sutras build .
          sutras publish --registry company
```

### Auto-Index Building

Add a GitHub Action to rebuild the index on push:

```yaml
# .github/workflows/build-index.yaml
name: Build Index

on:
  push:
    branches: [main]
    paths:
      - 'skills/**'
      - 'releases/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Sutras
        run: pip install sutras

      - name: Build Index
        run: sutras registry build-index .

      - name: Commit Index
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add index.yaml
          git diff --staged --quiet || git commit -m "Update index"
          git push
```

## Index Format Reference

The `index.yaml` structure:

```yaml
skills:
  "@namespace/skill-name":
    version: "1.2.0"
    description: "What this skill does"
    author: "Author Name"
    license: "MIT"
    tarball_url: "releases/skill-name-1.2.0.tar.gz"
    checksum: "sha256:a1b2c3d4..."
    versions:
      "1.2.0": "releases/skill-name-1.2.0.tar.gz"
      "1.1.0": "releases/skill-name-1.1.0.tar.gz"
      "1.0.0": "releases/skill-name-1.0.0.tar.gz"
    dependencies:
      - "@utils/common"
    tags:
      - "productivity"
      - "automation"
```

## Registry Maintenance

### Removing Old Versions

1. Delete the tarball from `releases/`
2. Remove version entry from `index.yaml`
3. Commit and push

### Deprecating Skills

Add a deprecation notice in the index:

```yaml
skills:
  "@namespace/old-skill":
    version: "1.0.0"
    deprecated: true
    deprecated_message: "Use @namespace/new-skill instead"
```

### Registry Backup

Since it's a Git repo, backups are simple:

```sh
git clone --mirror git@github.com:company/registry.git registry-backup.git
```

## Security Considerations

1. **Access Control** - Use Git repository permissions
2. **Code Review** - Require PR reviews before merge
3. **Checksums** - Sutras verifies SHA256 checksums on install
4. **Audit Trail** - Git history tracks all changes

## Troubleshooting

### "Permission denied (publickey)"

SSH key not configured correctly:
```sh
ssh -T git@github.com  # Test GitHub connection
```

### "Index not found"

Registry needs an `index.yaml`:
```sh
sutras registry build-index /path/to/registry
```

### "Skill not in index"

After adding a skill, rebuild the index:
```sh
sutras registry build-index .
git add index.yaml && git commit -m "Update index" && git push
```

Then update locally:
```sh
sutras registry update company
```

## Next Steps

- [Publishing Guide](publishing.md) - Learn to publish skills
- [Registry Guide](registry.md) - Registry usage details

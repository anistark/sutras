# sutras registry

Manage skill registries for discovering and distributing skills.

## Overview

Sutras uses a federated Git-based registry system:

- **No central infrastructure** - Registries are Git repositories
- **Private registries** - Use Git authentication for access control
- **Offline support** - Works with cached indexes
- **Multiple registries** - Priority ordering for search

---

## sutras registry add

Add a new registry.

### Usage

```sh
sutras registry add <name> <git-url> [OPTIONS]
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Registry name (for reference) | Yes |
| `git-url` | Git URL of the registry | Yes |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--namespace NS` | Default namespace for skills | None |
| `--priority N` | Search priority (higher = first) | 0 |
| `--default` | Set as default registry | False |

### Examples

```sh
# Add official registry
sutras registry add official https://github.com/anthropics/sutras-registry --default

# Add company registry with high priority
sutras registry add company https://github.com/mycompany/skills-registry --priority 10

# Add personal registry
sutras registry add personal https://github.com/myuser/my-skills
```

---

## sutras registry list

List all configured registries.

### Usage

```sh
sutras registry list
```

### Output

Displays a table with:

- Registry name
- Git URL
- Priority
- Default status
- Last updated

---

## sutras registry remove

Remove a registry from configuration.

### Usage

```sh
sutras registry remove <name>
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Registry name to remove | Yes |

### Example

```sh
sutras registry remove old-registry
```

---

## sutras registry update

Update registry index from remote.

### Usage

```sh
sutras registry update <name>
sutras registry update --all
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name` | Registry name to update | Yes (unless --all) |

### Options

| Option | Description |
|--------|-------------|
| `--all` | Update all registries |

### Examples

```sh
# Update specific registry
sutras registry update official

# Update all registries
sutras registry update --all
```

---

## sutras registry build-index

Build an index for a local registry.

### Usage

```sh
sutras registry build-index <path> [OPTIONS]
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `path` | Path to local registry directory | Yes |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output PATH` | Output path for index file | `<path>/index.json` |

### Example

```sh
sutras registry build-index ./my-registry
sutras registry build-index ./my-registry --output ./index.json
```

---

## Registry Setup Guide

### Setting up a personal registry

1. Create a Git repository
2. Add skill packages to the repository
3. Build the index:
   ```sh
   sutras registry build-index ./my-registry
   ```
4. Push to remote
5. Add to Sutras:
   ```sh
   sutras registry add personal https://github.com/you/my-registry
   ```

### Setting up a company registry

1. Create a private Git repository
2. Structure skills by namespace
3. Build and maintain the index
4. Team members add with priority:
   ```sh
   sutras registry add company https://github.com/company/skills --priority 10
   ```

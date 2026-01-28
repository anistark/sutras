# sutras install

Install skills from various sources.

## Usage

```sh
sutras install <SOURCE> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `SOURCE` | Skill source (see sources below) | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--version VERSION` | Specific version to install | Latest |
| `--registry NAME` | Registry to search | All registries |

## Source Formats

### From Registry

```sh
sutras install @namespace/skill-name
sutras install @namespace/skill-name --version 1.2.0
sutras install @namespace/skill-name --registry company-registry
```

### From GitHub Releases

```sh
# Latest release
sutras install github:username/repo

# Specific version
sutras install github:username/repo@v1.0.0
sutras install github:username/repo@1.0.0
```

### From URL

```sh
sutras install https://example.com/skills/my-skill-1.0.0.tar.gz
sutras install https://github.com/user/repo/releases/download/v1.0.0/skill.tar.gz
```

### From Local File

```sh
sutras install ./dist/my-skill-1.0.0.tar.gz
sutras install /path/to/skill.tar.gz
```

## Examples

### Install from registry

```sh
sutras install @username/skill-name
```

### Install specific version

```sh
sutras install @username/skill-name --version 1.2.0
```

### Install from GitHub

```sh
sutras install github:anistark/my-skill@v1.0.0
```

### Install from local build

```sh
sutras install ./dist/my-skill-1.0.0.tar.gz
```

## Installation Location

Installed skills are placed in:

- `~/.claude/installed/` - Versioned skill installations
- `~/.claude/skills/` - Symlinks to active versions

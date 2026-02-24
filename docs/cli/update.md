# sutras update

Check for updates and upgrade sutras to the latest version.

This command updates **all sutras components** in one step:

1. **Python CLI** — the `sutras` command itself (via pipx, uv, or pip)
2. **pi extension** — the `/sutras` commands in [pi](https://github.com/badlogic/pi) (via pi/pnpm/npm)
3. **Global skill** — the bundled `SKILL.md` in `~/.claude/skills/sutras/`

This ensures everything stays in sync after an upgrade — no more version drift between the CLI, the pi extension, and the skill definition.

## Usage

```sh
sutras update [OPTIONS]
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-v`, `--version TEXT` | Update to a specific version instead of latest | latest |
| `--check` | Only check if an update is available, don't install | False |
| `--skip-pi` | Skip updating the pi extension | False |
| `--skip-skill` | Skip refreshing the global skill (`~/.claude/skills/sutras/`) | False |

## Examples

### Check for updates

```sh
sutras update --check
```

Output when an update is available:
```
Current version: 0.4.0
Latest version:  0.4.1

Run sutras update to upgrade.
```

Output when already up-to-date:
```
Current version: 0.4.1
✓ Already up-to-date!
```

### Update everything to latest

```sh
sutras update
```

Output:
```
Updating sutras 0.4.0 → 0.4.1

✓ Python CLI updated (0.4.0 → 0.4.1)
✓ pi extension updated (0.4.1)
✓ Global skill updated (0.4.1)

✓ Update complete!
  Restart your terminal or pi session to use the new version.
```

### Pin to a specific version

```sh
sutras update -v 0.4.0
```

### Update CLI and skill only (skip pi)

```sh
sutras update --skip-pi
```

### Update CLI only

```sh
sutras update --skip-pi --skip-skill
```

## How It Works

### Version check

`sutras update --check` queries the [PyPI JSON API](https://pypi.org/pypi/sutras/json) and compares the latest published version against the currently installed one using semantic versioning.

### Python CLI upgrade

The command auto-detects how sutras was originally installed and uses the matching tool to upgrade:

| Installer detected | Upgrade command |
|-------------------|-----------------|
| pipx | `pipx upgrade sutras` |
| uv | `uv tool upgrade sutras` |
| pip / pip3 | `pip install --upgrade --user sutras` |

When pinning to a specific version (`-v`), it uses `--force` install with the exact version.

### pi extension upgrade

The pi extension is an npm package. The command tries these methods in order:

1. `pi pkg update sutras` — preferred if pi CLI is available
2. `pnpm update -g sutras` — fallback
3. `npm update -g sutras` — last resort

If none are available (e.g., pi is not installed), this step is silently skipped.

### Global skill refresh

After upgrading the CLI, the bundled `SKILL.md` inside the new package is written to `~/.claude/skills/sutras/SKILL.md`. This is equivalent to running [`sutras setup`](setup.md), ensuring Claude Code always sees the skill definition matching the installed CLI version.

If the skill content hasn't changed (same version), the write is skipped.

## Automatic upgrade on pi extension install

When the sutras pi extension is installed or updated via npm, a `postinstall` script automatically checks if the Python CLI version meets the minimum required version. If the installed CLI is too old, it upgrades it automatically. This means:

- `pi pkg update sutras` → npm postinstall triggers → Python CLI upgraded if needed

The `sutras update` command provides the reverse direction and a single entry point for upgrading everything manually.

## Troubleshooting

### "No suitable installer found"

The CLI upgrade requires one of: `pipx`, `uv`, `pip3`, or `pip`. Install one of them first:

```sh
# Recommended
brew install pipx   # macOS
apt install pipx    # Debian/Ubuntu

# Or use uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### pi extension skipped

If you see `pi extension skipped`, it means neither `pi`, `pnpm`, nor `npm` were found on your PATH. This is fine if you don't use pi — the CLI and skill are still updated.

### Version didn't change after update

If `sutras update` reports success but `sutras --version` still shows the old version, your shell may be caching the old binary path. Run:

```sh
hash -r          # bash/zsh
rehash           # fish
```

Or restart your terminal.

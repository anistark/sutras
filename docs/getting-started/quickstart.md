# Quickstart

Get started with Sutras in minutes.

## Create a New Skill

```sh
sutras new my-skill --description "What this skill does and when to use it"
```

This creates:

```sh
.claude/skills/my-skill/
├── SKILL.md           # Skill definition with YAML frontmatter
├── sutras.yaml        # Metadata (version, author, tests, etc.)
└── examples.md        # Usage examples
```

## List Skills

```sh
sutras list
```

## View Skill Details

```sh
sutras info my-skill
```

## Validate a Skill

```sh
sutras validate my-skill

# Strict mode (warnings become errors)
sutras validate my-skill --strict
```

## Build and Distribute

```sh
# Build a distributable package
sutras build my-skill

# Install from registry
sutras install @namespace/skill-name
```

## Next Steps

- Explore the [CLI Reference](../cli/index)
- See [example skills](https://github.com/anistark/sutras/tree/main/examples/skills/)

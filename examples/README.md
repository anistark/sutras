# Example Skills

This directory contains example skills demonstrating how to build Anthropic Agent Skills with Sutras.

## Directory Structure

```sh
examples/
└── skills/
    └── hello-claude/      # Simple greeting skill
        ├── SKILL.md       # Anthropic Skills format with YAML frontmatter
        ├── sutras.yaml    # Sutras ABI metadata
        └── examples.md    # Detailed usage examples
```

## Using Example Skills

### View Example Skills

You can inspect the example skills to understand the structure:

```sh
# View the SKILL.md
cat examples/skills/hello-claude/SKILL.md

# View the Sutras ABI
cat examples/skills/hello-claude/sutras.yaml
```

### Try the Examples

To try the example skills with Claude:

```sh
# Copy to your skills directory
cp -r examples/skills/hello-claude .claude/skills/

# View skill info
sutras info hello-claude

# Validate the skill
sutras validate hello-claude

# List all skills
sutras list
```

## Creating Your Own Skills

Use these examples as templates:

```sh
# Create a new skill
sutras new my-skill --description "Detailed description of what this skill does and when to use it"

# This creates:
# .claude/skills/my-skill/
# ├── SKILL.md
# ├── sutras.yaml
# └── examples.md

# Edit the files to customize your skill
```

## Example Skill: hello-claude

The `hello-claude` skill demonstrates:

1. **SKILL.md Structure**: Proper YAML frontmatter with name, description, and allowed-tools
2. **Clear Instructions**: Step-by-step guidance for Claude
3. **When to Use**: Specific trigger scenarios
4. **Examples**: Concrete use cases

### Key Features Demonstrated

- **Name**: `hello-claude` (lowercase, hyphen-separated)
- **Description**: Detailed explanation including what it does and when Claude should use it
- **Allowed Tools**: `Read, Write` (restricts which tools Claude can use)
- **Instructions**: Clear, numbered steps
- **Examples**: Multiple usage scenarios

### Sutras ABI Metadata

The `sutras.yaml` file shows:

- **Version**: Semantic versioning (`1.0.0`)
- **Author**: Skill author information
- **License**: License identifier (MIT)
- **Capabilities**: Tool declarations
- **Distribution**: Tags, category, keywords for discovery

## Best Practices

When creating skills based on these examples:

1. **Description is Critical**: Make it detailed with specific keywords Claude can match
2. **Be Specific**: Include file types, actions, and trigger words
3. **Clear Instructions**: Number steps and be explicit
4. **Provide Examples**: Show concrete usage scenarios
5. **Test with Validation**: Run `sutras validate` before using

## Learn More

- [Anthropic Skills Documentation](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Sutras README](../README.md)
- Create your first skill: `sutras new <skill-name>`

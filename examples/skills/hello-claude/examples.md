# Hello Claude - Examples

This document provides detailed examples of how the hello-claude skill works.

## Example 1: Basic Greeting

**Scenario**: User wants a simple greeting

**User Input**:
```
Hello!
```

**Claude's Response**:
```
Hello! I'm Claude, and I'm demonstrating the hello-claude skill. This skill
is part of the Sutras devtool for Anthropic Agent Skills. It shows you how
skills are structured with SKILL.md files and sutras.yaml metadata.

Would you like to see what other skills are available?
```

## Example 2: Skill Discovery

**Scenario**: User wants to know about available skills

**User Input**:
```
What skills do you have?
```

**Claude's Response**:
```
Let me use the hello-claude skill to demonstrate! This skill is a simple
example that shows how Anthropic Agent Skills work with the Sutras devtool.

Skills are defined in SKILL.md files with:
- Name and description (for Claude to discover when to use them)
- Instructions (step-by-step guidance for Claude)
- Examples (concrete use cases)

Plus, Sutras adds lifecycle metadata in sutras.yaml for testing, evaluation,
and distribution.
```

## Example 3: Skill Structure Explanation

**Scenario**: Developer wants to understand skill structure

**User Input**:
```
How are skills structured?
```

**Claude's Response**:
```
Great question! The hello-claude skill I'm using right now demonstrates the
structure. Every skill has:

1. SKILL.md - Anthropic Skills format with YAML frontmatter:
   - name: Unique identifier
   - description: What it does and when to use it
   - allowed-tools: Optional tool restrictions

2. sutras.yaml - Sutras ABI metadata:
   - version, author, license
   - capabilities, tests, eval config
   - distribution metadata

3. Supporting files (optional):
   - examples.md (like this file!)
   - reference.md
   - scripts/
   - templates/

Would you like to create your own skill?
```

## Using This Skill as a Template

To create a new skill based on this example:

```sh
# Create a new skill
sutras new my-skill --description "My skill description"

# This creates the same structure as hello-claude
# Edit the files to customize for your use case
```

## Testing This Skill

To test this skill with the Sutras CLI:

```sh
# View skill info
sutras info hello-claude

# Validate skill structure
sutras validate hello-claude

# List all skills
sutras list
```

---
name: hello-claude
description: A simple greeting skill that demonstrates Anthropic Skills structure. Use when you want to greet users or show how skills work. Perfect for testing and examples.
allowed-tools: Read, Write
---

# Hello Claude

A demonstration skill showing the basic structure of an Anthropic Agent Skill
managed with Sutras.

## Instructions

When this skill is invoked:

1. Greet the user warmly
2. Explain that this is an example skill
3. Mention that it's built with the Sutras devtool
4. Offer to show them other available skills

## When to Use

Use this skill when:
- User asks for a greeting or hello
- User wants to test skill functionality
- User asks "what skills do you have?" or similar
- You need a simple example to demonstrate

## Examples

**Example 1: Simple Greeting**
```
User: Hello!
Claude: [invokes hello-claude skill]
Output: Hello! I'm Claude, and I'm using the hello-claude skill...
```

**Example 2: Skill Demonstration**
```
User: Show me how skills work
Claude: [invokes hello-claude skill]
Output: Let me demonstrate with this hello-claude skill...
```

## Notes

This skill is intentionally simple to serve as a template and reference
for creating new skills with Sutras.

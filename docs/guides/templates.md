# Skill Templates

Templates help you scaffold new skills with pre-configured content for common
use cases. Instead of starting from a blank slate, templates provide structured
SKILL.md instructions, appropriate tool declarations, and example test cases.

## Using Templates

### List available templates

```sh
sutras new --list-templates
```

### Create a skill from a template

```sh
sutras new my-skill --template <template-name>
```

If no `--template` is specified, the `default` template is used.

## Built-in Templates

### default

A minimal scaffold with placeholder sections. Best for skills that don't fit
into a specific category.

```sh
sutras new my-skill
```

### code-review

Pre-configured for code review workflows. Includes:

- `Read` and `Bash` tool declarations
- Structured review output format (summary, issues, suggestions)
- Test case for reviewing a simple function

```sh
sutras new my-reviewer --template code-review
```

### api-integration

Designed for API client and integration skills. Includes:

- `Read`, `Write`, and `Bash` tool declarations
- Guidelines for auth, error handling, and rate limiting
- Test case for generating client code

```sh
sutras new stripe-client --template api-integration
```

### data-analysis

For skills that process and analyze data files. Includes:

- `Read`, `Write`, and `Bash` tool declarations
- Guidelines for data profiling and reporting
- Test case for CSV analysis

```sh
sutras new sales-analyzer --template data-analysis
```

### automation

For workflow automation and scripting skills. Includes:

- `Read`, `Write`, and `Bash` tool declarations
- Guidelines for idempotency, dry-run modes, and logging
- Test case for generating automation scripts

```sh
sutras new deploy-helper --template automation
```

## Customising After Creation

Templates are a starting point. After creating a skill, you should:

1. Edit `SKILL.md` to refine the instructions for your specific use case
2. Update `sutras.yaml` with your author info, tags, and category
3. Add real test cases to `sutras.yaml`
4. Run `sutras validate <name>` to check the skill structure

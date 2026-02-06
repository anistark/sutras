"""Built-in skill templates for scaffolding new skills."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillTemplate:
    """A skill template defining the scaffolded file contents."""

    name: str
    description: str
    skill_md: str
    sutras_yaml: str
    examples_md: str
    extra_files: dict[str, str] = field(default_factory=dict)


def _default_template() -> SkillTemplate:
    return SkillTemplate(
        name="default",
        description="Minimal skill scaffold with basic structure",
        skill_md="""\
---
name: {name}
description: {description}
---

# {title}

## Instructions

Add your skill instructions here. Provide step-by-step guidance for Claude
on how to use this skill effectively.

1. First step
2. Second step
3. Third step

## When to Use

Describe the scenarios when Claude should invoke this skill.

## Examples

Provide concrete examples of how this skill works.
""",
        sutras_yaml="""\
version: "0.1.0"
author: "{author}"
license: "MIT"

capabilities:
  tools: []
  dependencies: []
  constraints: {{}}

distribution:
  tags: []
  category: "general"
""",
        examples_md="""\
# {title} - Examples

## Example 1: Basic Usage

Description of basic usage scenario.

## Example 2: Advanced Usage

Description of advanced usage scenario.
""",
    )


def _code_review_template() -> SkillTemplate:
    return SkillTemplate(
        name="code-review",
        description="Code review skill with diff analysis and feedback patterns",
        skill_md="""\
---
name: {name}
description: {description}
allowed-tools: Read, Bash
---

# {title}

## Instructions

You are a code review assistant. When invoked:

1. Read the files or diff provided by the user
2. Analyze the code for:
   - Correctness and potential bugs
   - Style and readability
   - Performance concerns
   - Security issues
3. Provide structured feedback with line references
4. Suggest concrete improvements with code examples

## When to Use

Use this skill when:
- User asks for a code review
- User shares a diff or pull request
- User asks "what do you think of this code?"
- User wants feedback on implementation quality

## Output Format

Structure your review as:
- **Summary**: One-line overall assessment
- **Issues**: Categorized findings (bug, style, perf, security)
- **Suggestions**: Actionable improvements with examples
""",
        sutras_yaml="""\
version: "0.1.0"
author: "{author}"
license: "MIT"

capabilities:
  tools: [Read, Bash]
  dependencies: []
  constraints: {{}}

tests:
  cases:
    - name: "review-simple-function"
      inputs:
        code: "def add(a, b): return a + b"
      expected:
        has_feedback: true

distribution:
  tags: ["code-review", "developer-tools", "quality"]
  category: "development"
""",
        examples_md="""\
# {title} - Examples

## Example 1: Review a Function

```
User: Review this function:
def get_user(id):
    conn = sqlite3.connect("db.sqlite")
    return conn.execute(f"SELECT * FROM users WHERE id = {{id}}").fetchone()
```

**Expected output**: Identifies SQL injection risk, missing connection cleanup,
and suggests parameterized queries.

## Example 2: Review a Diff

```
User: Review this PR diff
```

**Expected output**: Structured feedback covering changes, potential issues,
and suggestions.
""",
    )


def _api_integration_template() -> SkillTemplate:
    return SkillTemplate(
        name="api-integration",
        description="API integration skill with request handling and error patterns",
        skill_md="""\
---
name: {name}
description: {description}
allowed-tools: Read, Write, Bash
---

# {title}

## Instructions

You are an API integration assistant. When invoked:

1. Understand the target API from documentation or user description
2. Write clean request/response handling code
3. Include proper error handling and retries
4. Add authentication setup where needed
5. Generate types or models for API responses

## When to Use

Use this skill when:
- User needs to integrate with a REST or GraphQL API
- User asks to write API client code
- User needs help with authentication flows (OAuth, API keys)
- User wants to generate types from an API schema

## Guidelines

- Always validate response status codes
- Use environment variables for secrets, never hardcode them
- Add timeout configuration
- Include rate limiting awareness
- Generate typed models for API responses
""",
        sutras_yaml="""\
version: "0.1.0"
author: "{author}"
license: "MIT"

capabilities:
  tools: [Read, Write, Bash]
  dependencies: []
  constraints: {{}}

tests:
  cases:
    - name: "generates-client-code"
      inputs:
        api: "REST"
        endpoint: "/users"
      expected:
        has_error_handling: true

distribution:
  tags: ["api", "integration", "http", "rest"]
  category: "integration"
""",
        examples_md="""\
# {title} - Examples

## Example 1: REST API Client

```
User: Create a client for the GitHub API to list repositories
```

**Expected output**: A typed client with auth, pagination, and error handling.

## Example 2: OAuth Integration

```
User: Set up OAuth2 authentication for a Slack app
```

**Expected output**: OAuth flow implementation with token refresh.
""",
    )


def _data_analysis_template() -> SkillTemplate:
    return SkillTemplate(
        name="data-analysis",
        description="Data analysis skill with file processing and reporting patterns",
        skill_md="""\
---
name: {name}
description: {description}
allowed-tools: Read, Write, Bash
---

# {title}

## Instructions

You are a data analysis assistant. When invoked:

1. Read and understand the data source (CSV, JSON, database, logs)
2. Identify the structure, types, and quality of the data
3. Perform the requested analysis or transformation
4. Present findings with clear summaries and visualisation suggestions
5. Write output files when requested

## When to Use

Use this skill when:
- User provides data files for analysis
- User asks to parse, transform, or summarize data
- User needs data quality checks or profiling
- User wants to generate reports from data

## Guidelines

- Always describe the data shape before analysis
- Handle missing values and encoding issues gracefully
- Suggest appropriate chart types for the data
- Provide both summary statistics and notable outliers
""",
        sutras_yaml="""\
version: "0.1.0"
author: "{author}"
license: "MIT"

capabilities:
  tools: [Read, Write, Bash]
  dependencies: []
  constraints: {{}}

tests:
  cases:
    - name: "analyze-csv"
      inputs:
        format: "csv"
        rows: 100
      expected:
        has_summary: true

distribution:
  tags: ["data", "analysis", "csv", "reporting"]
  category: "data"
""",
        examples_md="""\
# {title} - Examples

## Example 1: CSV Analysis

```
User: Analyze this sales CSV and summarize trends
```

**Expected output**: Data shape summary, key statistics, trend observations,
and suggested visualisations.

## Example 2: Log Parsing

```
User: Parse these server logs and find the most common errors
```

**Expected output**: Error frequency table, timeline, and root-cause grouping.
""",
    )


def _automation_template() -> SkillTemplate:
    return SkillTemplate(
        name="automation",
        description="Workflow automation skill with task orchestration patterns",
        skill_md="""\
---
name: {name}
description: {description}
allowed-tools: Read, Write, Bash
---

# {title}

## Instructions

You are a workflow automation assistant. When invoked:

1. Understand the manual process the user wants to automate
2. Break it down into discrete, repeatable steps
3. Write scripts or configuration to automate each step
4. Add error handling and logging
5. Provide clear setup and execution instructions

## When to Use

Use this skill when:
- User wants to automate a repetitive task
- User needs a CI/CD pipeline or GitHub Action
- User asks to script a multi-step workflow
- User wants to set up scheduled tasks or hooks

## Guidelines

- Make automation idempotent where possible
- Add dry-run modes for destructive operations
- Log each step for debuggability
- Keep configuration separate from logic
- Fail fast and report clearly on errors
""",
        sutras_yaml="""\
version: "0.1.0"
author: "{author}"
license: "MIT"

capabilities:
  tools: [Read, Write, Bash]
  dependencies: []
  constraints: {{}}

tests:
  cases:
    - name: "generates-automation-script"
      inputs:
        task: "backup"
      expected:
        has_error_handling: true

distribution:
  tags: ["automation", "workflow", "scripting", "ci-cd"]
  category: "automation"
""",
        examples_md="""\
# {title} - Examples

## Example 1: Deployment Script

```
User: Create a deployment script for my Node.js app
```

**Expected output**: A script with build, test, deploy steps, rollback support,
and environment configuration.

## Example 2: GitHub Action

```
User: Set up a CI pipeline that runs tests and deploys on merge to main
```

**Expected output**: A GitHub Actions workflow YAML with test, lint, and deploy jobs.
""",
    )


BUILT_IN_TEMPLATES: dict[str, SkillTemplate] = {}


def _register_built_ins() -> None:
    for factory in [
        _default_template,
        _code_review_template,
        _api_integration_template,
        _data_analysis_template,
        _automation_template,
    ]:
        t = factory()
        BUILT_IN_TEMPLATES[t.name] = t


_register_built_ins()


def list_templates() -> list[SkillTemplate]:
    """Return all available templates sorted by name."""
    return sorted(BUILT_IN_TEMPLATES.values(), key=lambda t: t.name)


def get_template(name: str) -> SkillTemplate:
    """Get a template by name.

    Raises:
        ValueError: If template name is not found.
    """
    if name not in BUILT_IN_TEMPLATES:
        available = ", ".join(sorted(BUILT_IN_TEMPLATES))
        raise ValueError(f"Unknown template '{name}'. Available: {available}")
    return BUILT_IN_TEMPLATES[name]


def render_template(
    template: SkillTemplate,
    name: str,
    description: str,
    author: str,
) -> dict[str, str]:
    """Render a template with the given variables.

    Returns:
        Dict mapping filename to rendered content.
    """
    title = name.replace("-", " ").title()
    variables = {
        "name": name,
        "title": title,
        "description": description,
        "author": author,
    }

    files = {
        "SKILL.md": template.skill_md.format(**variables),
        "sutras.yaml": template.sutras_yaml.format(**variables),
        "examples.md": template.examples_md.format(**variables),
    }

    for filename, content in template.extra_files.items():
        files[filename] = content.format(**variables)

    return files

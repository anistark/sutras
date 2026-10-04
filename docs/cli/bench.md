# sutras bench

Benchmark a skill across models to see whether it holds up beyond the model it was written for.

`sutras bench` runs each case in the skill's `bench` section on every selected model through [Claude Code](https://code.claude.com/docs) in headless mode, grades every run, and compares pass rates against a baseline model. Before spending anything it shows the available models, the plan, an estimated cost range, and asks for approval.

## Usage

```sh
sutras bench <name|path> [OPTIONS]
```

## Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `name\|path` | Skill name or path to a skill directory | Yes |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--models` | Comma-separated model IDs or aliases, optionally `model@effort` | `bench.models`, else Opus, Sonnet, Haiku (current generation) |
| `--baseline` | Model to compare against | `bench.baseline`, else first model |
| `--runs` | Runs per case per model | `bench.runs` (3) |
| `--cases` | Comma-separated subset of case names | All cases |
| `--max-cost` | Hard spend cap in USD | `bench.max_cost`, else none |
| `--yes`, `-y` | Skip the approval prompt (requires a cap) | False |
| `--dry-run` | Show models, plan, and estimate without running | False |
| `--pilot` | Run one case per model first to calibrate the estimate | False |
| `--record` | Write the latest complete run into `sutras.yaml` | False |
| `--report md` | Also write a Markdown report | — |
| `--history` | List previous bench runs | False |
| `--parallel` | Concurrent runs | 2 |
| `--keep-sandbox` | Keep run workspaces for debugging | False |
| `--path` | Custom skills directory to search for `name` | — |

## Requirements

- [Claude Code](https://code.claude.com/docs) installed and signed in (`claude` on `PATH`)
- Optional: `pip install sutras[bench]` to list the models your Anthropic API credentials can use and to count tokens for the estimate. Without it, sutras falls back to Claude Code's model aliases and approximate token counts.

## Defining Cases

Add a `bench` section to `sutras.yaml`:

```yaml
bench:
  baseline: claude-opus-5-5
  models: [claude-opus-5-5, claude-sonnet-5-5, claude-haiku-4-5]
  runs: 5
  max_regression: 0.10      # flag models >10 points below the baseline pass rate
  max_cost: 10.00
  timeout: 600              # seconds per run
  judge: claude-opus-5-5    # fixed model that grades rubrics
  allowed_tools: []         # tools pre-approved for every case, e.g. "Bash(pytest *)"
  cases:
    - name: rename-symbol
      prompt: "Rename `foo` to `bar` across the project"
      workspace: bench/rename          # copied into the sandbox as the project root
      should_trigger: true
      allowed_tools: ["Bash(pytest *)"]
      assert:
        - type: command_succeeds
          run: pytest -q
        - type: file_contains
          path: src/app.py
          text: "def bar("
      rubric:
        - Does not modify files unrelated to the rename

    - name: unrelated-request
      prompt: "What's the capital of France?"
      should_trigger: false            # the skill must not load
```

### Assertions

| Type | Fields | Passes when |
|------|--------|-------------|
| `output_contains` | `text` | The final response contains `text` |
| `output_matches` | `pattern` | The final response matches the regex |
| `file_exists` | `path` | The file exists in the workspace after the run |
| `file_contains` | `path`, `text` | The file contains `text` |
| `file_unchanged` | `path` | The file is identical to the original workspace copy |
| `command_succeeds` | `run`, `timeout` | The shell command exits 0 in the workspace |
| `tool_called` / `tool_not_called` | `tool` | The agent did / didn't call the tool |

A run passes when the skill's trigger behavior matches `should_trigger`, every assertion passes, and every rubric criterion is graded as met. The judge only runs when everything else already passed.

## How Runs Are Isolated

Each run gets a fresh temporary project with the skill installed in `.claude/skills/`. Claude Code is started with only project-level settings (`--setting-sources project`), no MCP servers, no session persistence, and with edits allowed but every other permission prompt denied. Your personal skills, user settings, and hooks don't load.

`command_succeeds` commands run on your machine inside the sandbox directory, and the plan lists them before you approve.

## Cost Estimate and Cap

The estimate is a range, and the plan states how it was produced:

- **history** — per-run costs from earlier bench runs of this skill
- **pilot** — a `--pilot` calibration run (one case per model)
- **heuristic** — SKILL.md and prompt tokens (exact with `sutras[bench]`) plus assumed turns and output

Actual spend comes from Claude Code's per-run cost report. With `--max-cost`, no run starts if it could push spend past the cap, and each run is also capped by Claude Code with the remaining budget. On a Claude subscription, costs are API-equivalent estimates that draw from your plan's usage limits.

Prices come from a built-in table. Override them in `~/.sutras/config.yaml`:

```yaml
pricing:
  claude-opus-5-5: {input: 4.0, output: 20.0}   # USD per million tokens
```

## Results

- Every run is saved to `<skill>/.sutras/bench/<timestamp>.json` (not included in `sutras build` packages)
- `--report md` writes a Markdown summary next to it, suitable for PR comments
- `--record` writes a `compatibility` summary into `sutras.yaml`, which ships with the skill. `sutras info` shows it as "Tested on", `sutras validate` warns when the skill changed since, and `sutras registry build-index` includes it in the registry index

The command exits non-zero when a model regresses past `max_regression` or the run is incomplete.

## Examples

### Preview models, plan, and cost

```sh
sutras bench my-skill --dry-run
```

### Compare two models with a budget

```sh
sutras bench my-skill --models opus,sonnet --runs 5 --max-cost 5
```

### Compare effort levels

```sh
sutras bench my-skill --models claude-opus-5-5@low,claude-opus-5-5@high
```

### CI

```sh
sutras bench my-skill --yes --max-cost 10 --report md
```

### Record results for distribution

```sh
sutras bench my-skill --record
```

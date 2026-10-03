"""Claude Code runtime executor (headless ``claude -p``)."""

import json
import re
import shutil
import subprocess
import time
from typing import Any

from sutras.core.pricing import MODEL_ALIASES, ModelPrice, get_price
from sutras.core.runtime.base import (
    ModelDiscovery,
    ModelInfo,
    RunRequest,
    RunResult,
    TokenUsage,
    ToolCall,
)

_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


class ClaudeCodeExecutor:
    """Runs skills through the Claude Code CLI in print mode.

    Each run is isolated from the host configuration: only project-level
    settings and skills from the sandbox are loaded (``--setting-sources
    project``), no MCP servers connect (``--strict-mcp-config``), nothing is
    persisted, and anything that would prompt for permission is denied.
    """

    name = "claude-code"

    def __init__(self, binary: str = "claude"):
        self.binary = binary

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def version(self) -> str | None:
        try:
            proc = subprocess.run(
                [self.binary, "--version"], capture_output=True, text=True, timeout=15
            )
        except (OSError, subprocess.SubprocessError):
            return None
        match = _VERSION_RE.search(proc.stdout)
        return match.group(0) if match else None

    def discover_models(
        self, price_overrides: dict[str, ModelPrice] | None = None
    ) -> ModelDiscovery:
        """List models via the Anthropic Models API, falling back to Claude Code aliases."""
        note: str
        try:
            import anthropic  # type: ignore[import-not-found]

            client = anthropic.Anthropic(timeout=15.0, max_retries=1)
            models = [
                ModelInfo(
                    id=m.id,
                    display_name=getattr(m, "display_name", None),
                    price=get_price(m.id, price_overrides),
                )
                for m in client.models.list()
                if m.id.startswith("claude")
            ]
            if models:
                return ModelDiscovery(models=models, source="api")
            note = "The Models API returned no Claude models"
        except ImportError:
            note = "Install 'sutras[bench]' to list the models your API credentials can use"
        except Exception as e:
            note = (
                f"Could not query the Models API ({type(e).__name__}); showing Claude Code aliases"
            )

        models = [
            ModelInfo(id=model_id, display_name=alias, price=get_price(model_id, price_overrides))
            for alias, model_id in MODEL_ALIASES.items()
        ]
        return ModelDiscovery(models=models, source="aliases", note=note)

    def build_command(self, request: RunRequest) -> list[str]:
        cmd = [
            self.binary,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            request.model,
            "--setting-sources",
            "project",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--permission-mode",
            "acceptEdits",
            "--permission-prompts",
            "none",
        ]
        if request.effort:
            cmd += ["--effort", request.effort]
        if request.max_budget_usd is not None:
            cmd += ["--max-budget-usd", f"{max(request.max_budget_usd, 0.01):.4f}"]
        if request.tools is not None:
            cmd += ["--tools", ",".join(request.tools)]
        if request.json_schema is not None:
            cmd += ["--json-schema", json.dumps(request.json_schema)]
        if request.allowed_tools:
            cmd += ["--allowed-tools", *request.allowed_tools]
        return cmd

    def run(self, request: RunRequest) -> RunResult:
        cmd = self.build_command(request)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=request.prompt,
                capture_output=True,
                text=True,
                cwd=request.cwd,
                timeout=request.timeout,
            )
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            result = parse_stream_json(stdout, request.model)
            result.cost_usd = None
            result.error = f"Timed out after {request.timeout}s"
            result.duration_s = time.monotonic() - start
            return result
        except OSError as e:
            return RunResult(model=request.model, error=f"Failed to start Claude Code: {e}")

        result = parse_stream_json(proc.stdout, request.model)
        result.duration_s = time.monotonic() - start
        if proc.returncode != 0 and result.error is None:
            stderr = proc.stderr.strip().splitlines()
            result.error = stderr[-1] if stderr else f"Claude Code exited with {proc.returncode}"
        return result


def parse_stream_json(stdout: str, model: str) -> RunResult:
    """Build a RunResult from Claude Code ``--output-format stream-json`` output."""
    result = RunResult(model=model)
    last_text = ""
    final: dict[str, Any] | None = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        if event.get("type") == "assistant":
            message = event.get("message") or {}
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                    call = ToolCall(name=str(block.get("name", "")), input=tool_input)
                    result.tool_calls.append(call)
                    if call.name == "Skill":
                        skill = tool_input.get("skill") or tool_input.get("command")
                        if skill:
                            result.skills_invoked.append(str(skill).lstrip("/"))
                elif block.get("type") == "text" and not event.get("parent_tool_use_id"):
                    last_text = block.get("text", "") or last_text
        elif event.get("type") == "result":
            final = event

    if final is None:
        result.final_text = last_text
        result.error = "Claude Code produced no result event"
        return result

    result.final_text = final.get("result") or last_text
    result.num_turns = int(final.get("num_turns") or 0)
    cost = final.get("total_cost_usd")
    result.cost_usd = float(cost) if isinstance(cost, int | float) else None
    result.usage = TokenUsage.from_dict(final.get("usage"))
    result.structured_output = final.get("structured_output")

    subtype = final.get("subtype")
    if final.get("is_error") or (subtype and subtype != "success"):
        detail = final.get("result") if final.get("is_error") else None
        result.error = f"{subtype or 'error'}: {detail}" if detail else str(subtype or "error")
    return result

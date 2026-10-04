"""Deterministic assertions evaluated after each bench run."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sutras.core.abi import BenchAssertion
from sutras.core.runtime.base import RunResult
from sutras.core.sandbox import Sandbox


@dataclass
class AssertionOutcome:
    """Result of a single assertion."""

    description: str
    passed: bool
    message: str = ""


def describe(assertion: BenchAssertion) -> str:
    """Short human-readable label for an assertion."""
    match assertion.type:
        case "output_contains":
            return f"output contains {assertion.text!r}"
        case "output_matches":
            return f"output matches /{assertion.pattern}/"
        case "file_exists":
            return f"{assertion.path} exists"
        case "file_contains":
            return f"{assertion.path} contains {assertion.text!r}"
        case "file_unchanged":
            return f"{assertion.path} unchanged"
        case "command_succeeds":
            return f"`{assertion.run}` succeeds"
        case "tool_called":
            return f"{assertion.tool} called"
        case "tool_not_called":
            return f"{assertion.tool} not called"
    return assertion.type


def evaluate(assertion: BenchAssertion, result: RunResult, sandbox: Sandbox) -> AssertionOutcome:
    """Evaluate one assertion against a run's output and final workspace."""
    label = describe(assertion)
    try:
        passed, message = _check(assertion, result, sandbox)
    except ValueError as e:
        passed, message = False, str(e)
    return AssertionOutcome(description=label, passed=passed, message=message)


def _check(assertion: BenchAssertion, result: RunResult, sandbox: Sandbox) -> tuple[bool, str]:
    tools_used = {call.name for call in result.tool_calls}

    match assertion.type:
        case "output_contains":
            return str(assertion.text) in result.final_text, ""
        case "output_matches":
            return re.search(str(assertion.pattern), result.final_text) is not None, ""
        case "file_exists":
            return sandbox.resolve(str(assertion.path)).exists(), ""
        case "file_contains":
            path = sandbox.resolve(str(assertion.path))
            if not path.is_file():
                return False, "file not found"
            return str(assertion.text) in _read(path), ""
        case "file_unchanged":
            path = sandbox.resolve(str(assertion.path))
            original = (sandbox.workspace / str(assertion.path)) if sandbox.workspace else None
            if original is None or not original.is_file():
                return not path.exists(), "file was created"
            if not path.is_file():
                return False, "file was deleted"
            return path.read_bytes() == original.read_bytes(), ""
        case "command_succeeds":
            return _run_command(str(assertion.run), sandbox.root, assertion.timeout)
        case "tool_called":
            return assertion.tool in tools_used, ""
        case "tool_not_called":
            return assertion.tool not in tools_used, ""
    return False, f"unknown assertion type '{assertion.type}'"


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return path.read_bytes().decode(errors="replace")


def _run_command(command: str, cwd: Path, timeout: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    if proc.returncode == 0:
        return True, ""
    output = (proc.stderr or proc.stdout).strip().splitlines()
    return False, f"exit {proc.returncode}" + (f": {output[-1]}" if output else "")

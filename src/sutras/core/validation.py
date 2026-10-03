"""Helpers and limits used by skill validation (``sutras validate``)."""

import re
from urllib.parse import unquote

MAX_NAME_LENGTH = 64
"""Maximum skill name length allowed by the Anthropic Agent Skills spec."""

MAX_DESCRIPTION_LENGTH = 1024
"""Maximum skill description length allowed by the Anthropic Agent Skills spec."""

# NOTE: Built-in Claude Code tool names. Unknown names are reported as warnings
# (not errors) since this list can lag behind new Claude Code releases.
KNOWN_TOOLS = frozenset(
    {
        "Agent",
        "AskUserQuestion",
        "Bash",
        "BashOutput",
        "Edit",
        "EnterPlanMode",
        "ExitPlanMode",
        "Glob",
        "Grep",
        "KillShell",
        "LS",
        "Monitor",
        "MultiEdit",
        "NotebookEdit",
        "NotebookRead",
        "Read",
        "Skill",
        "SlashCommand",
        "Task",
        "TodoWrite",
        "ToolSearch",
        "WebFetch",
        "WebSearch",
        "Write",
    }
)

_TOOL_ENTRY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)(\(.*\))?$")
_FENCED_CODE_RE = re.compile(r"^(```|~~~).*?^\1", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def parse_tool_entry(entry: str) -> str | None:
    """Extract the base tool name from an allowed-tools entry.

    Handles plain names (``Read``), permission patterns (``Bash(git:*)``) and
    MCP tools (``mcp__server__tool``).

    Returns:
        The base tool name, or None if the entry is malformed
    """
    match = _TOOL_ENTRY_RE.match(entry.strip())
    return match.group(1) if match else None


def is_known_tool(name: str) -> bool:
    """Check whether a base tool name is a known Claude Code or MCP tool."""
    return name in KNOWN_TOOLS or name.startswith("mcp__")


def extract_file_references(markdown: str) -> list[str]:
    """Find relative file paths referenced by markdown links and images.

    Links inside fenced or inline code, URLs (``https:``, ``mailto:``, ...),
    pure anchors (``#section``) and absolute paths are ignored. Anchors and
    query strings are stripped and percent-encoding is decoded.

    Returns:
        Unique referenced paths, in order of first appearance
    """
    text = _FENCED_CODE_RE.sub("", markdown)
    text = _INLINE_CODE_RE.sub("", text)

    refs: list[str] = []
    for target in _LINK_RE.findall(text):
        if target.startswith(("#", "/")) or _URL_SCHEME_RE.match(target):
            continue
        path = unquote(re.split(r"[#?]", target, maxsplit=1)[0])
        if path and path not in refs:
            refs.append(path)
    return refs

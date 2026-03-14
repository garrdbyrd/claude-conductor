#!/usr/bin/env python3
"""Merge conductor MCP permissions into the user's global ~/.claude/settings.json."""
import json
import pathlib

SETTINGS_PATH = pathlib.Path.home() / ".claude" / "settings.json"

MCP_TOOLS = [
    "mcp__conductor__init_player",
    "mcp__conductor__register_project",
    "mcp__conductor__create_task",
    "mcp__conductor__start_task",
    "mcp__conductor__complete_task",
    "mcp__conductor__block_task",
    "mcp__conductor__request_input",
    "mcp__conductor__reset_task",
    "mcp__conductor__log_update",
    "mcp__conductor__list_tasks",
    "mcp__conductor__get_task_log",
]


def main():
    settings = {}
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text())
        except json.JSONDecodeError:
            pass

    permissions = settings.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])

    changed = False
    for tool in MCP_TOOLS:
        if tool not in allow:
            allow.append(tool)
            changed = True

    if changed:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")


if __name__ == "__main__":
    main()

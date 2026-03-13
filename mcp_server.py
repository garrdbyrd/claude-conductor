#!/usr/bin/env python3
"""
mcp_server.py — FastMCP SSE server for claude-conductor.

Player Claude sessions connect to this server to register projects,
manage tasks, and log progress updates.

Run:  uv run mcp_server.py
SSE:  http://localhost:8766/sse
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
import db as _db

mcp = FastMCP("claude-conductor", host="0.0.0.0", port=8766)

# Shared connection (WAL mode handles concurrent access fine for this load)
_conn = None


def conn():
    global _conn
    if _conn is None:
        _db.init_db()
        _conn = _db.get_conn()
    return _conn


# ── Init tool ────────────────────────────────────────────────────────────────

@mcp.tool()
def init_player(repo_path: str, project_id: str, name: str,
                description: str = "", color: str = "") -> dict:
    """Initialize this repo as a conductor player session.

    Call this ONCE at the very start of a new player session (before anything else).
    It writes CONDUCTOR.md and .claude/settings.json with the correct permissions,
    then registers the project in the conductor database.

    - repo_path: absolute path to this repo (use os.getcwd())
    - project_id: short unique slug, e.g. "myproject"
    - name: human-readable display name
    - description: one-sentence summary
    - color: hex color, e.g. "#a855f7" (auto-assigned if omitted)
    """
    import pathlib, json
    from init_player_lib import make_settings, CONDUCTOR_MD, get_color_for_index

    repo = pathlib.Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        return {"ok": False, "error": f"{repo} is not a directory"}

    # Assign color by position so consecutive projects are maximally distinct
    if color:
        chosen_color = color
    else:
        project_count = len(_db.get_all_projects(conn()))
        chosen_color = get_color_for_index(project_count)

    # Write .claude/settings.json
    claude_dir = repo / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings_path.write_text(json.dumps(make_settings(repo), indent=2) + "\n")

    # Write CONDUCTOR.md
    (repo / "CONDUCTOR.md").write_text(CONDUCTOR_MD)

    # Register in DB
    proj = _db.upsert_project(
        conn(),
        id=project_id,
        name=name,
        description=description,
        color=chosen_color,
        repo_path=str(repo),
    )

    return {
        "ok": True,
        "message": "Player initialized. Now call list_tasks to see existing work, or create_task to begin.",
        "project": proj,
    }


# ── Project tools ─────────────────────────────────────────────────────────────

@mcp.tool()
def register_project(
    project_id: str,
    name: str,
    description: str = "",
    color: str = "#388bfd",
    repo_path: str = "",
) -> dict:
    """Register this repo as a conductor player project.

    Call this once at the start of a player session.
    - project_id: short slug, e.g. "myproject" (must be unique)
    - name: human-readable display name
    - description: one-sentence summary of what the project is
    - color: hex color for the Kanban board, e.g. "#a855f7"
    - repo_path: absolute path to the player repo (use os.getcwd())

    Returns the project record.
    """
    proj = _db.upsert_project(
        conn(),
        id=project_id,
        name=name,
        description=description,
        color=color,
        repo_path=repo_path,
    )
    return {"ok": True, "project": proj}


# ── Task tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_task(project_id: str, title: str, description: str = "") -> dict:
    """Create a new task for your project. Returns the task record with its id.

    Create tasks at the start of a session or whenever new work is identified.
    Tasks start in 'todo' status.
    """
    task = _db.create_task(conn(), project_id=project_id, title=title, description=description)
    return {"ok": True, "task": task}


@mcp.tool()
def start_task(task_id: str, message: str = "") -> dict:
    """Mark a task as 'in_progress'. Call this BEFORE starting the work, not after.

    This is the most important rule: update the board first, then do the work.
    - message: brief description of what you're about to do
    """
    task = _db.update_task_status(conn(), task_id, "in_progress", message)
    return {"ok": True, "task": task}


@mcp.tool()
def complete_task(task_id: str, message: str = "") -> dict:
    """Mark a task as 'done'. Call this after the work is fully complete.

    - message: brief summary of what was accomplished
    """
    task = _db.update_task_status(conn(), task_id, "done", message)
    return {"ok": True, "task": task}


@mcp.tool()
def block_task(task_id: str, reason: str) -> dict:
    """Mark a task as 'blocked'. Use when you cannot proceed.

    - reason: explain what is blocking progress
    """
    task = _db.update_task_status(conn(), task_id, "blocked", reason)
    return {"ok": True, "task": task}


@mcp.tool()
def request_input(task_id: str, question: str) -> dict:
    """Signal that you need human input before you can continue.

    This moves the task to 'needs_input' and prominently flags it on the
    conductor's Kanban board. The conductor will see it and respond.

    Use this whenever you are blocked on a decision, missing information,
    or need clarification — NOT for technical errors (use block_task for those).

    - question: clearly state what you need. Be specific.

    The conductor will resolve it and your task will return to in_progress.
    """
    task = _db.update_task_status(conn(), task_id, "needs_input", f"Waiting for input: {question}")
    return {"ok": True, "task": task}


@mcp.tool()
def reset_task(task_id: str, message: str = "") -> dict:
    """Move a task back to 'todo' (e.g. to un-block or re-queue it)."""
    task = _db.update_task_status(conn(), task_id, "todo", message)
    return {"ok": True, "task": task}


@mcp.tool()
def log_update(task_id: str, message: str) -> dict:
    """Add a progress log entry to a task.

    Use this frequently to keep the conductor informed. Log BEFORE taking
    an action so the board reflects what's happening in real time.

    Good examples:
    - "About to refactor auth module"
    - "Running test suite to check for regressions"
    - "Committing: add user login endpoint"
    """
    _db.append_log(conn(), task_id, message)
    return {"ok": True, "task_id": task_id}


# ── Query tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_tasks(project_id: str) -> dict:
    """List all tasks for your project with their current status."""
    tasks = _db.get_tasks_for_project(conn(), project_id)
    return {"tasks": tasks}


@mcp.tool()
def get_task_log(task_id: str) -> dict:
    """Get the full log history for a task."""
    logs = _db.get_logs_for_task(conn(), task_id)
    return {"task_id": task_id, "log": logs}


if __name__ == "__main__":
    _db.init_db()
    _conn = _db.get_conn()
    print("MCP server → http://localhost:8766/sse", flush=True)
    mcp.run(transport="sse")

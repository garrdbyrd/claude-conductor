# Claude Conductor

You are the **conductor** — the master orchestrator for parallel Claude player sessions.

## Your Role

- Answer questions about project status by querying the SQLite DB
- Start the system with `bash start.sh` (done automatically on session open via the Start hook)
- Initialize player repos when asked

## Starting the System

```bash
bash start.sh
```

Starts both servers and registers the MCP globally. The Start hook in `.claude/settings.local.json` runs this automatically when you open this repo.

## Initializing a Player

```bash
uv run init-player.py --repo /path/to/repo --name "Project Name" --description "..."
```

Or, from within any Claude session, call the `init_player` MCP tool directly.

## Querying Status

```python
import db
conn = db.get_conn()
status = db.as_kanban_json(conn)        # full board as dict
tasks  = db.get_tasks_for_project(conn, "project-id")
logs   = db.get_logs_for_task(conn, "task-id")
```

Or via sqlite3:

```bash
sqlite3 conductor.db \
  "SELECT p.name, t.status, t.title, t.updated_at
   FROM tasks t JOIN projects p ON t.project_id=p.id
   ORDER BY t.updated_at DESC"
```

## Python

Always use `uv run` — never bare `python` or `python3`.

## Ports

- **WebUI** → http://localhost:9095
- **MCP server** → http://localhost:8766/sse

"""
db.py — SQLite database layer for claude-conductor.
Shared by the MCP server, web server, and any conductor-side queries.
"""
import sqlite3
import datetime
import uuid
import pathlib

DB_PATH = pathlib.Path(__file__).parent / "conductor.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # concurrent reads during writes
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                color       TEXT NOT NULL DEFAULT '#388bfd',
                repo_path   TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          TEXT PRIMARY KEY,
                project_id  TEXT NOT NULL REFERENCES projects(id),
                title       TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status      TEXT NOT NULL DEFAULT 'todo',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS task_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id    TEXT NOT NULL REFERENCES tasks(id),
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
            CREATE INDEX IF NOT EXISTS idx_logs_task    ON task_logs(task_id);
        """)


def now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def make_id(prefix: str = "") -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}-{suffix}" if prefix else suffix


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_all_projects(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


def get_tasks_for_project(conn, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at",
        (project_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_logs_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM task_logs WHERE task_id = ? ORDER BY created_at",
        (task_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def as_kanban_json(conn) -> dict:
    """Return the full DB as JSON in the Kanban UI format."""
    projects = {}
    for proj in get_all_projects(conn):
        tasks = []
        for task in get_tasks_for_project(conn, proj["id"]):
            logs = get_logs_for_task(conn, task["id"])
            tasks.append({
                "id":         task["id"],
                "title":      task["title"],
                "description": task["description"],
                "status":     task["status"],
                "updated_at": task["updated_at"],
                "log": [{"time": lg["created_at"], "message": lg["message"]} for lg in logs],
            })
        projects[proj["id"]] = {
            "name":        proj["name"],
            "description": proj["description"],
            "color":       proj["color"],
            "repo_path":   proj["repo_path"],
            "tasks":       tasks,
        }
    return {"projects": projects}


# ── Write helpers ─────────────────────────────────────────────────────────────

def upsert_project(conn, *, id: str, name: str, description: str = "",
                   color: str = "#388bfd", repo_path: str = "") -> dict:
    existing = conn.execute("SELECT id FROM projects WHERE id = ?", (id,)).fetchone()
    ts = now()
    if existing:
        conn.execute(
            "UPDATE projects SET name=?, description=?, color=?, repo_path=?, updated_at=? WHERE id=?",
            (name, description, color, repo_path, ts, id)
        )
    else:
        conn.execute(
            "INSERT INTO projects(id,name,description,color,repo_path,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (id, name, description, color, repo_path, ts, ts)
        )
    conn.commit()
    return dict(conn.execute("SELECT * FROM projects WHERE id=?", (id,)).fetchone())


def create_task(conn, *, project_id: str, title: str, description: str = "") -> dict:
    task_id = make_id(project_id)
    ts = now()
    conn.execute(
        "INSERT INTO tasks(id,project_id,title,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (task_id, project_id, title, description, "todo", ts, ts)
    )
    conn.execute(
        "INSERT INTO task_logs(task_id,message,created_at) VALUES(?,?,?)",
        (task_id, "Task created", ts)
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


def update_task_status(conn, task_id: str, status: str, message: str = "") -> dict:
    ts = now()
    conn.execute(
        "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
        (status, ts, task_id)
    )
    log_msg = f"Status → {status}" + (f": {message}" if message else "")
    conn.execute(
        "INSERT INTO task_logs(task_id,message,created_at) VALUES(?,?,?)",
        (task_id, log_msg, ts)
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


def append_log(conn, task_id: str, message: str) -> None:
    ts = now()
    conn.execute(
        "INSERT INTO task_logs(task_id,message,created_at) VALUES(?,?,?)",
        (task_id, message, ts)
    )
    conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (ts, task_id))
    conn.commit()

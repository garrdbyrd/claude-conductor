#!/usr/bin/env python3
"""Kanban web server — serves the live agent dashboard on port 9095."""
import sys
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from http.server import HTTPServer, BaseHTTPRequestHandler
import db as _db

INDEX = pathlib.Path(__file__).parent / "index.html"
PORT = 9095

_conn = None


def conn():
    global _conn
    if _conn is None:
        _db.init_db()
        _conn = _db.get_conn()
    return _conn


VALID_STATUSES = {"todo", "in_progress", "done", "blocked", "needs_input"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/db":
            data = json.dumps(_db.as_kanban_json(conn()), indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif self.path in ("/", "/index.html"):
            data = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid JSON"})
            return

        if self.path == "/api/task/resolve":
            # Move a needs_input task back to in_progress
            task_id = payload.get("task_id", "")
            if not task_id:
                self._respond(400, {"error": "missing task_id"})
                return
            task = _db.update_task_status(
                conn(), task_id, "in_progress",
                "Input provided by conductor — resuming"
            )
            self._respond(200, {"ok": True, "task": task})

        elif self.path == "/api/task/status":
            # Generic status update from the UI
            task_id = payload.get("task_id", "")
            status  = payload.get("status", "")
            message = payload.get("message", "")
            if not task_id or status not in VALID_STATUSES:
                self._respond(400, {"error": "missing/invalid task_id or status"})
                return
            task = _db.update_task_status(conn(), task_id, status, message)
            self._respond(200, {"ok": True, "task": task})

        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress per-request logs


if __name__ == "__main__":
    _db.init_db()
    _conn = _db.get_conn()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Kanban UI → http://localhost:{PORT}", flush=True)
    server.serve_forever()

#!/usr/bin/env python3
"""
conductor.py — Main launcher for claude-conductor.

Starts the Kanban WebUI and MCP SSE server in parallel.
Run this once when beginning a conductor session.

Usage:
    uv run conductor.py
"""
import subprocess
import sys
import pathlib
import threading
import time

BASE = pathlib.Path(__file__).parent


def run_server(script: pathlib.Path, label: str):
    proc = subprocess.Popen(
        ["uv", "run", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Print first line (the "listening on..." message) then let it run
    first = proc.stdout.readline()
    if first.strip():
        print(f"  [{label}] {first.strip()}")
    # Drain output in background so the pipe doesn't fill up
    def drain():
        for line in proc.stdout:
            pass
    threading.Thread(target=drain, daemon=True).start()
    return proc


def main():
    import db as _db
    _db.init_db()
    print("Claude Conductor starting…")

    webui = run_server(BASE / "webui" / "server.py", "webui")
    mcp   = run_server(BASE / "mcp_server.py",        "mcp  ")

    print()
    print("  Kanban UI  → http://localhost:9095")
    print("  MCP server → http://localhost:8766/sse")
    print()
    print("Both servers are running. Press Ctrl+C to stop.")
    print()

    try:
        while True:
            # Restart either process if it dies unexpectedly
            if webui.poll() is not None:
                print("[webui] crashed, restarting…")
                webui = run_server(BASE / "webui" / "server.py", "webui")
            if mcp.poll() is not None:
                print("[mcp] crashed, restarting…")
                mcp = run_server(BASE / "mcp_server.py", "mcp  ")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down…")
        webui.terminate()
        mcp.terminate()


if __name__ == "__main__":
    main()

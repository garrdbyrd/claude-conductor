# Claude Conductor

Orchestrate multiple autonomous Claude Code sessions from a single Kanban board. A **conductor** session runs the dashboard and MCP server; **player** sessions self-register and report progress in real time.

```
                   Conductor
        ┌─────────────────────────┐
        │  Kanban WebUI  :9095    │
        │  MCP Server    :8766    │
        └────────────┬────────────┘
                     │  MCP tools
          ┌──────────┼──────────┐
       Player A   Player B   Player C
       /my-app    /api-srv   /ml-pipe
```

## Quick Start

```bash
git clone https://github.com/YOUR_USER/claude-conductor ~/claude-conductor
cd ~/claude-conductor
bash start.sh
```

This installs dependencies, starts both servers, and registers the MCP globally. Open http://localhost:9095 to see the board.

On future sessions the conductor auto-starts via a [Start hook](.claude/settings.json).

## Adding a Player

Open Claude Code in any repo on this machine. The conductor MCP tools are already available globally. Tell the agent:

> Read CONDUCTOR.md and initialize yourself as a player.

Or pre-initialize a repo from the CLI:

```bash
cd ~/claude-conductor
uv run init-player.py --repo ~/my-project --name "My Project"
```

The player calls `init_player` on startup, which registers the project, writes a `CONDUCTOR.md` guide, and sets up permissions so the agent can work autonomously.

## Kanban Board

| Column | Meaning |
|--------|---------|
| **Needs Input** | Blocked on a human decision — check this first |
| **Todo** | Queued |
| **In Progress** | Active |
| **Done** | Complete |
| **Blocked** | Technical blocker, no human needed |

- Auto-refreshes every 5 seconds
- Click a project name in the legend to show/hide it
- Click **Mark Resolved** on a Needs Input card to unblock the player

## MCP Tools

All tools are available in every Claude Code session on this machine.

| Tool | What it does |
|------|-------------|
| `init_player` | Register a repo as a player project |
| `create_task` | Add a task (starts as todo) |
| `start_task` | Move to in_progress (**before** doing the work) |
| `complete_task` | Move to done |
| `block_task` | Move to blocked (technical issue) |
| `request_input` | Flag for human input (shows alert on board) |
| `reset_task` | Return to todo |
| `log_update` | Add a progress note |
| `list_tasks` | List tasks for a project |
| `get_task_log` | Full log history for a task |

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/)
- Python 3.11+

## Ports

| Service | Default | Config file |
|---------|---------|-------------|
| Kanban WebUI | 9095 | `webui/server.py` |
| MCP server | 8766 | `mcp_server.py` |

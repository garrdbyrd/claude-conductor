"""
Shared logic for initializing player sessions.
Used by both init-player.py (CLI) and the init_player MCP tool.
"""
import json
import pathlib

MCP_HOST = "localhost"
MCP_PORT = 8766

# Ordered for maximum contrast between adjacent projects.
# Assignment is positional (first project gets index 0, second gets index 1, etc.)
# so the board always cycles through visually distinct colors in a predictable order.
COLORS = [
    "#ef4444",  # 0 red
    "#3fb950",  # 1 green
    "#388bfd",  # 2 blue
    "#eab308",  # 3 yellow
    "#a855f7",  # 4 purple
    "#f97316",  # 5 orange
    "#14b8a6",  # 6 teal
    "#ec4899",  # 7 pink
    "#84cc16",  # 8 lime
    "#06b6d4",  # 9 cyan
    "#f43f5e",  # 10 rose
    "#8b5cf6",  # 11 violet
]


def pick_color(project_id: str) -> str:
    """Deterministically assign a color based on hash — used only as fallback.
    Prefer positional assignment via get_color_for_index() when order is known."""
    return COLORS[abs(hash(project_id)) % len(COLORS)]


def get_color_for_index(index: int) -> str:
    """Assign colors in order so consecutive projects are maximally distinct."""
    return COLORS[index % len(COLORS)]


def make_settings(repo: pathlib.Path) -> dict:
    """Generate a full .claude/settings.json for a player session."""
    r = str(repo)
    return {
        "mcpServers": {
            "conductor": {
                "type": "http",
                "url": f"http://{MCP_HOST}:{MCP_PORT}/mcp",
            }
        },
        "permissions": {
            "allow": [
                # Conductor MCP tools — all pre-approved
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
                "Read(*)",
                f"Write({r}/**)",
                f"Edit({r}/**)",
                "Glob(*)",
                "Grep(*)",
                "Bash(*)",
            ],
            "deny": [
                "Bash(sudo *)", "Bash(su *)", "Bash(doas *)",
                "Bash(pkexec *)", "Bash(runuser *)",
                "Bash(ssh *)", "Bash(scp *)", "Bash(sftp *)",
                "Bash(ftp *)", "Bash(nc *)", "Bash(ncat *)",
                "Bash(socat *)", "Bash(telnet *)",
                "Bash(apt *)", "Bash(apt-get *)", "Bash(dpkg *)",
                "Bash(rpm *)", "Bash(yum *)", "Bash(dnf *)",
                "Bash(pacman *)", "Bash(zypper *)", "Bash(apk *)",
                "Bash(snap *)", "Bash(flatpak *)",
                "Bash(brew install *)", "Bash(brew upgrade *)",
                "Bash(brew uninstall *)",
                "Bash(systemctl *)", "Bash(service *)",
                "Bash(launchctl *)", "Bash(initctl *)",
                "Bash(rc-service *)", "Bash(shutdown *)",
                "Bash(reboot *)", "Bash(halt *)", "Bash(poweroff *)",
                "Bash(mkfs*)", "Bash(fdisk *)", "Bash(gdisk *)",
                "Bash(parted *)", "Bash(mount *)", "Bash(umount *)",
                "Bash(losetup *)", "Bash(cryptsetup *)",
                "Bash(dd if=* of=/dev/*)", "Bash(dd of=/dev/*)",
                "Bash(iptables *)", "Bash(ip6tables *)",
                "Bash(nftables *)", "Bash(ufw *)",
                "Bash(firewall-cmd *)", "Bash(ifconfig *)",
                "Bash(ip link set *)", "Bash(ip addr add *)",
                "Bash(ip route add *)",
                "Bash(insmod *)", "Bash(rmmod *)",
                "Bash(modprobe *)", "Bash(sysctl -w *)",
                "Bash(crontab *)", "Bash(at *)",
            ],
        },
    }


CONDUCTOR_MD = """\
# Conductor Integration

You are a **player** session connected to the Claude Conductor orchestration system.
The conductor can see your project's Kanban board in real time.

## Startup Checklist

1. Call `init_player` with your project details — this registers the project and sets up
   permissions. It is idempotent, so it's safe to call every session.
2. Call `list_tasks` to see existing tasks and their statuses.
3. Pick up where you left off, or create new tasks with `create_task`.

## MCP Tools Available

| Tool | Purpose |
|------|---------|
| `init_player` | Initialize/re-register this project (call on every session start) |
| `register_project` | Update project metadata only (name, description, color) |
| `create_task` | Create a new task |
| `start_task` | Move task → in_progress (call **before** starting work) |
| `complete_task` | Move task → done |
| `block_task` | Move task → blocked |
| `reset_task` | Move task → todo |
| `request_input` | Pause and flag task — conductor must respond before you continue |
| `log_update` | Add a progress note to a task |
| `list_tasks` | List all tasks for your project |
| `get_task_log` | Get the full log for a task |

## The Golden Rule

> **Update the board BEFORE taking the action.**

Examples:
- Before running tests: `log_update(task_id, "Running test suite")`
- Before a git commit: `log_update(task_id, "Committing: <summary>")`
- Before starting a refactor: `start_task(task_id, "Refactoring auth module")`

## Kanban Workflow

```
todo  →  in_progress  →  done
               ↓
          needs_input  (conductor responds → back to in_progress)
               ↓
            blocked  →  todo (when unblocked)
```

- Move a task to **in_progress** before you touch its code.
- Use **needs_input** when you need a human decision to continue.
- Use **blocked** for technical/external blockers with no human needed.
- Move to **done** only when fully complete (tests pass, committed).

## Logging Frequency

Log at these moments (at minimum):
- When you start a task
- Before each git commit
- When you discover something unexpected
- When you finish a task

## Python

Always use `uv run` — never bare `python` or `python3`.

## Scope

Only modify files inside your project repository.
"""

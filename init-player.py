#!/usr/bin/env python3
"""
init-player.py — Initialize a repository as a conductor player session (CLI).

For most cases, prefer calling the `init_player` MCP tool directly from
within a Claude session — it does the same thing without this script.

Usage:
    uv run init-player.py --repo /path/to/repo [options]

Options:
    --repo PATH         Path to the player repository (required)
    --name NAME         Display name for the project (default: directory name)
    --id ID             Project ID slug (default: directory name, lowercased)
    --color COLOR       Hex color for the Kanban board (default: auto-assigned)
    --description TEXT  One-sentence project description
"""
import argparse
import json
import pathlib
import sys

from init_player_lib import make_settings, CONDUCTOR_MD, pick_color, get_color_for_index


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo",        required=True)
    parser.add_argument("--name",        default=None)
    parser.add_argument("--id",          default=None)
    parser.add_argument("--color",       default=None)
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    repo = pathlib.Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(f"Error: {repo} is not a directory.", file=sys.stderr)
        sys.exit(1)

    name        = args.name or repo.name
    project_id  = (args.id or repo.name).lower().replace(" ", "-")
    description = args.description
    # Color: explicit > positional from DB > hash fallback (no DB access here)
    color       = args.color or pick_color(project_id)

    claude_dir = repo / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps(make_settings(repo), indent=2) + "\n")
    print(f"✓ settings.json written")

    (repo / "CONDUCTOR.md").write_text(CONDUCTOR_MD)
    print(f"✓ CONDUCTOR.md written")

    print()
    print(f"Player ready: id={project_id!r} name={name!r} color={color}")
    print(f"Start a Claude session in {repo} and call init_player() to register.")


if __name__ == "__main__":
    main()

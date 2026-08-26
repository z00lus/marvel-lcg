#!/usr/bin/env python3
"""Register the repository's headless-player MCP server in Codex."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


MCP_NAME = "marvel_lcg"
SKILL_NAME = "marvel-lcg-player"


def run(*args: str, check: bool=True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:2345",
        help="URL of the running Ronin Edition server",
    )
    parser.add_argument(
        "--password",
        default="",
        help="Optional server password (stored in Codex MCP configuration)",
    )
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    repository_skill = repository / ".agents" / "skills" / SKILL_NAME
    mcp_server = repository / "tools" / "marvel_lcg_mcp.py"
    if not (repository_skill / "SKILL.md").is_file():
        raise FileNotFoundError(f"Repository skill was not found: {repository_skill}")
    if not mcp_server.is_file():
        raise FileNotFoundError(f"MCP server was not found: {mcp_server}")

    configured = run("codex", "mcp", "get", MCP_NAME, check=False)
    if configured.returncode == 0:
        run("codex", "mcp", "remove", MCP_NAME)

    command = [
        "codex", "mcp", "add", MCP_NAME,
        "--env", f"MARVEL_LCG_URL={args.server_url.rstrip('/')}",
    ]
    if args.password:
        command += ["--env", f"MARVEL_LCG_PASSWORD={args.password}"]
    command += ["--", "/usr/bin/python3", str(mcp_server)]
    run(*command)

    print(f"Repository skill: {repository_skill}")
    print(f"Configured MCP: {MCP_NAME} -> {args.server_url.rstrip('/')}")
    print("Open Codex in this repository and restart it once so the MCP becomes available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only, bounded startup context for local ClarityLink work."""
import json
import os
import subprocess
import sys

def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=1)

try:
    root = git("rev-parse", "--show-toplevel").stdout.strip()
    if not root:
        raise RuntimeError("current directory is not inside a Git worktree")
    branch = git("branch", "--show-current").stdout.strip() or "DETACHED"
    origin = git("remote", "get-url", "origin").stdout.strip()
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    status = git("status", "--short").stdout.strip()
    lines = [f"ClarityLink checkout: {root}", f"Branch: {branch}", f"origin: {origin or 'MISSING'}",
             f"upstream: {upstream.stdout.strip() if upstream.returncode == 0 else 'MISSING'}"]
    if status:
        lines.append("Worktree has local changes; inventory before editing or publishing.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }}))
except Exception as exc:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": f"ClarityLink repository audit could not complete: {exc}. Preserve local state and inspect Git manually.",
    }}))

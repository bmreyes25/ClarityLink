#!/usr/bin/env python3
"""Read-only, bounded startup context for local ClarityLink work."""
import json
import subprocess

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
    canonical = {
        "https://github.com/bmreyes25/ClarityLink.git",
        "git@github.com:bmreyes25/ClarityLink.git",
        "ssh://git@github.com/bmreyes25/ClarityLink.git",
    }
    upstream_name = upstream.stdout.strip() if upstream.returncode == 0 else ""
    ownership = "detached HEAD; create a task-owned feature branch before editing"
    if branch != "DETACHED":
        listing = git("worktree", "list", "--porcelain").stdout
        worktrees = []
        current_path = None
        current_branch = None
        for line in listing.splitlines() + [""]:
            if line.startswith("worktree "):
                current_path = line[9:]
            elif line.startswith("branch "):
                current_branch = line[7:]
            elif line == "" and current_path:
                worktrees.append((current_path, current_branch))
                current_path = None
                current_branch = None
        branch_owners = [path for path, ref in worktrees if ref == f"refs/heads/{branch}"]
        if len(branch_owners) == 1 and branch_owners[0] == root:
            ownership = f"branch {branch} is registered to this worktree"
        else:
            ownership = "current worktree registration is ambiguous; do not edit until branch ownership is resolved"
    lines = [f"ClarityLink checkout: {root}", f"Branch: {branch}", f"origin: {origin or 'MISSING'}",
             f"origin identity: {'canonical' if origin in canonical else 'MISMATCH — do not publish'}",
             f"upstream: {upstream_name or 'MISSING'}",
             f"upstream identity: {'matches branch' if upstream_name == f'origin/{branch}' else 'MISMATCH — verify branch before publishing'}",
             f"branch ownership: {ownership}"]
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

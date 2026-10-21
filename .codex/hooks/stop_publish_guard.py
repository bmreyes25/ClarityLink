#!/usr/bin/env python3
"""Bounded read-only publication audit; never commits or pushes."""
import json
import os
import subprocess
import sys

def respond(value):
    print(json.dumps(value))

try:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception:
        event = {}
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=1).stdout.strip()
    if not root:
        respond({})
        raise SystemExit(0)
    audit = subprocess.run([sys.executable, os.path.join(root, "tools/verify_remote_publication.py"),
                            "--repo", root, "--timeout", "1"], capture_output=True, text=True, timeout=2)
    try:
        result = json.loads(audit.stdout)
    except Exception:
        result = {"result": "NO_REMOTE_BRANCH", "reason": "publication audit unavailable"}
    if result.get("result") == "REMOTE_VERIFIED":
        respond({})
    else:
        reason = result.get("result", "UNKNOWN")
        detail = result.get("reason", "local change or unverified remote state")
        if event.get("stop_hook_active") is True:
            respond({"systemMessage": f"Publication remains incomplete ({reason}: {detail}). The Stop hook already continued once; preserve state and report the blocker."})
        else:
            respond({"decision": "block", "reason": f"ClarityLink publication audit: {reason} ({detail}). Continue this turn. Review only the task's explicit public-safe file scope, then use tools/publish_checkpoint.sh with VERIFIED or WIP_UNVERIFIED. Never stage unknown files. If blocked, preserve local state and report the exact blocker."})
except Exception as exc:
    respond({"systemMessage": f"ClarityLink publication audit could not complete safely: {exc}. Preserve local state and inspect publication manually."})

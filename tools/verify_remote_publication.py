#!/usr/bin/env python3
"""Verify a branch against its live GitHub ref; local tracking refs are not proof."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = "bmreyes25/ClarityLink"
CANONICAL = {f"https://github.com/{REPO}.git", f"git@github.com:{REPO}.git", f"ssh://git@github.com/{REPO}.git"}


def git(root: Path, *args: str, timeout: float = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, timeout=timeout)


def run(root: Path, branch: str | None = None, pr: int | None = None, timeout: float = 5) -> dict:
    root = Path(git(root, "rev-parse", "--show-toplevel", timeout=timeout).stdout.strip() or root)
    if git(root, "rev-parse", "--git-dir", timeout=timeout).returncode != 0:
        return {"result": "NO_REMOTE_BRANCH", "reason": "not a Git repository"}
    url = git(root, "remote", "get-url", "origin", timeout=timeout)
    if url.returncode or url.stdout.strip() not in CANONICAL:
        return {"result": "NO_REMOTE_BRANCH", "reason": "origin is absent or not canonical ClarityLink"}
    current = git(root, "branch", "--show-current", timeout=timeout).stdout.strip()
    branch = branch or current
    if not branch:
        return {"result": "NO_REMOTE_BRANCH", "reason": "detached HEAD"}
    if current and current != branch:
        return {"result": "REMOTE_SHA_MISMATCH", "branch": branch, "current_branch": current,
                "reason": "requested branch is not the checked out branch"}
    head = git(root, "rev-parse", "HEAD", timeout=timeout).stdout.strip()
    upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", timeout=timeout)
    if upstream.returncode or upstream.stdout.strip() != f"origin/{branch}":
        return {"result": "NO_REMOTE_BRANCH", "branch": branch, "head": head,
                "reason": "configured upstream is missing or does not match origin/branch"}
    status = git(root, "status", "--porcelain", timeout=timeout).stdout.splitlines()
    source_pending = [line for line in status if not line[3:].startswith(("build/", ".pytest_cache/", "__pycache__/"))]
    remote = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}", timeout=timeout)
    if remote.returncode:
        error = (remote.stderr or "").lower()
        result = "AUTHENTICATION_FAILURE" if "auth" in error or "permission denied" in error else "NO_REMOTE_BRANCH"
        return {"result": result, "branch": branch, "head": head, "reason": remote.stderr.strip()[:500]}
    line = remote.stdout.strip().split()
    if not line:
        return {"result": "NO_REMOTE_BRANCH", "branch": branch, "head": head, "uncommitted_source_count": len(source_pending)}
    remote_sha = line[0]
    if remote_sha != head:
        ancestry = git(root, "merge-base", "--is-ancestor", remote_sha, head, timeout=timeout)
        result = "UNPUSHED_COMMITS" if ancestry.returncode == 0 else "REMOTE_SHA_MISMATCH"
        count = git(root, "rev-list", "--count", f"{remote_sha}..HEAD", timeout=timeout)
        return {"result": result, "branch": branch, "head": head, "remote_sha": remote_sha,
                "unpushed_commit_count": int(count.stdout.strip() or "0"),
                "uncommitted_source_count": len(source_pending)}
    if source_pending:
        return {"result": "LOCAL_CHANGES_PENDING", "branch": branch, "head": head, "remote_sha": remote_sha,
                "uncommitted_source_count": len(source_pending)}
    output = {"result": "REMOTE_VERIFIED", "repository": REPO, "branch": branch, "head": head,
              "remote_sha": remote_sha, "upstream": upstream.stdout.strip() if upstream.returncode == 0 else None,
              "unpushed_commit_count": 0, "uncommitted_source_count": 0, "pr": None}
    if pr:
        gh = subprocess.run(["gh", "pr", "view", str(pr), "-R", REPO, "--json", "url,headRefName,state"],
                            text=True, capture_output=True, timeout=timeout)
        if gh.returncode:
            output["result"] = "NO_REMOTE_BRANCH"
            output["reason"] = (gh.stderr or "PR lookup failed").strip()[:500]
        else:
            data = json.loads(gh.stdout)
            output["pr"] = data
            if data.get("headRefName") != branch:
                output["result"] = "REMOTE_SHA_MISMATCH"
                output["reason"] = "PR head does not match branch"
    return output


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path.cwd())
    p.add_argument("--branch")
    p.add_argument("--pr", type=int)
    p.add_argument("--timeout", type=float, default=5)
    p.add_argument("--push-rejected", action="store_true", help="report a failed push attempt")
    p.add_argument("--unsafe-content-blocked", action="store_true", help="report a content safety rejection")
    args = p.parse_args()
    if args.push_rejected:
        result = {"result": "PUSH_REJECTED", "reason": "push was rejected; local state must be preserved"}
        print(json.dumps(result, sort_keys=True))
        return 1
    if args.unsafe_content_blocked:
        result = {"result": "UNSAFE_CONTENT_BLOCKED", "reason": "publication scope failed safety scanning"}
        print(json.dumps(result, sort_keys=True))
        return 1
    try:
        result = run(args.repo, args.branch, args.pr, args.timeout)
    except subprocess.TimeoutExpired:
        result = {"result": "NO_REMOTE_BRANCH", "reason": "remote inspection timed out"}
    except OSError as e:
        result = {"result": "NO_REMOTE_BRANCH", "reason": str(e)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "REMOTE_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
